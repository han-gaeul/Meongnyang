from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.pagination import DefaultCursorPagination
from common.permissions import IsOwnerOrReadOnly, IsVerifiedMember
from common.visibility import visible_to
from moderation.serializers import ReportCreateSerializer, ReportResultSerializer
from moderation.services import report_content

from .models import Gathering, Participation
from .serializers import ApplySerializer, GatheringSerializer, ParticipationSerializer

# 시작 시간이 이만큼 지나면 목록에서 내린다
LIST_GRACE = timedelta(hours=3)


class UpcomingPagination(DefaultCursorPagination):
    ordering = ("starts_at", "id")  # 가까운 일정부터


class GatheringViewSet(viewsets.ModelViewSet):
    serializer_class = GatheringSerializer
    pagination_class = UpcomingPagination
    owner_field = "host"

    def get_permissions(self):
        if self.action in {"create", "apply", "cancel", "report"}:
            return [IsVerifiedMember()]
        if self.action in {"update", "partial_update", "destroy", "applications", "decide"}:
            return [IsOwnerOrReadOnly()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Gathering.objects.none()
        user = self.request.user
        qs = (
            visible_to(Gathering.objects.all(), user, author_field="host")
            .select_related("host")
            .prefetch_related(
                Prefetch("participations", queryset=Participation.objects.select_related("user", "pet"))
            )
            .annotate(n_accepted=Count("participations", filter=Q(participations__status="accepted")))
        )
        if self.action != "list":
            return qs
        p = self.request.query_params
        if kind := p.get("kind"):
            qs = qs.filter(kind=kind)
        if species := p.get("species"):
            if species in ("dog", "cat"):
                qs = qs.filter(species__in=[species, "all"])
        if region := p.get("region"):
            qs = qs.filter(region_name=region)
        if p.get("mine") == "1":
            qs = qs.filter(Q(host=user) | Q(participations__user=user)).distinct()
        else:
            qs = qs.filter(starts_at__gte=timezone.now() - LIST_GRACE).exclude(status=Gathering.Status.CANCELLED)
        return qs

    @extend_schema(
        parameters=[
            OpenApiParameter("kind", str, enum=["walk", "share"]),
            OpenApiParameter("species", str, enum=["dog", "cat"]),
            OpenApiParameter("region", str),
            OpenApiParameter("mine", str, enum=["1"], description="내가 연/참여한 모임(지난 것 포함)"),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(host=user, region_name=user.region_name)

    def _fresh(self, pk):
        return self.get_queryset().get(pk=pk)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        self.perform_create(s)
        return Response(self.get_serializer(self._fresh(s.instance.pk)).data, status=201)

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        gathering = Gathering.objects.get(pk=kwargs["pk"])
        gathering.refresh_status()  # 정원을 바꾼 경우
        return Response(self.get_serializer(self._fresh(gathering.pk)).data)

    def perform_destroy(self, instance):
        # 참여자가 있으면 지우지 않고 취소 처리 (참여자에게 기록이 남도록)
        if instance.participations.exclude(status__in=["rejected", "cancelled"]).exists():
            instance.status = Gathering.Status.CANCELLED
            instance.save(update_fields=["status", "updated_at"])
        else:
            instance.delete()

    @extend_schema(request=ApplySerializer, responses={200: GatheringSerializer})
    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        gathering = self.get_object()
        user = request.user
        if gathering.host_id == user.id:
            return Response({"detail": "내가 연 모임이에요."}, status=400)
        if gathering.status != Gathering.Status.OPEN or gathering.starts_at < timezone.now():
            return Response({"detail": "모집이 끝난 모임이에요."}, status=400)
        s = ApplySerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)

        existing = Participation.objects.filter(gathering=gathering, user=user).first()
        if existing and existing.status in (Participation.Status.PENDING, Participation.Status.ACCEPTED):
            return Response({"detail": "이미 신청한 모임이에요."}, status=409)
        if existing and existing.status == Participation.Status.REJECTED:
            return Response({"detail": "모임장이 거절한 모임에는 다시 신청할 수 없어요."}, status=400)
        Participation.objects.update_or_create(
            gathering=gathering,
            user=user,
            defaults={"pet": s.validated_data.get("pet"), "message": s.validated_data["message"],
                      "status": Participation.Status.PENDING, "decided_at": None},
        )
        return Response(self.get_serializer(self._fresh(gathering.pk)).data)

    @extend_schema(request=None, responses={200: GatheringSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """내 참여 신청 취소 (수락 후에도 가능, 자리가 나면 다시 모집 중)"""
        gathering = self.get_object()
        p = Participation.objects.filter(
            gathering=gathering, user=request.user, status__in=["pending", "accepted"]
        ).first()
        if p is None:
            return Response({"detail": "취소할 신청이 없어요."}, status=400)
        p.status = Participation.Status.CANCELLED
        p.save(update_fields=["status"])
        gathering.refresh_status()
        return Response(self.get_serializer(self._fresh(gathering.pk)).data)

    @extend_schema(responses={200: ParticipationSerializer(many=True)})
    @action(detail=True, methods=["get"], pagination_class=None)
    def applications(self, request, pk=None):
        """신청자 목록 (모임장만)"""
        gathering = self.get_object()
        if gathering.host_id != request.user.id:
            return Response({"detail": "모임장만 볼 수 있어요."}, status=403)
        qs = gathering.participations.select_related("user", "pet").exclude(status="cancelled")
        return Response(ParticipationSerializer(qs, many=True).data)

    @extend_schema(
        request=None,
        parameters=[OpenApiParameter("decision", str, location="path", enum=["accept", "reject"])],
        responses={200: ParticipationSerializer},
    )
    @action(detail=True, methods=["post"], url_path=r"applications/(?P<pid>\d+)/(?P<decision>accept|reject)")
    def decide(self, request, pk=None, pid=None, decision=None):
        """신청 수락·거절 (모임장만)"""
        gathering = self.get_object()
        if gathering.host_id != request.user.id:
            return Response({"detail": "모임장만 할 수 있어요."}, status=403)
        with transaction.atomic():
            g = Gathering.objects.select_for_update().get(pk=gathering.pk)
            p = Participation.objects.filter(pk=pid, gathering=g).first()
            if p is None or p.status != Participation.Status.PENDING:
                return Response({"detail": "처리할 수 없는 신청이에요."}, status=400)
            if decision == "accept":
                if g.status == Gathering.Status.CANCELLED:
                    return Response({"detail": "취소된 모임이에요."}, status=400)
                if g.count_accepted() >= g.capacity:
                    return Response({"detail": "정원이 다 찼어요."}, status=400)
                p.status = Participation.Status.ACCEPTED
            else:
                p.status = Participation.Status.REJECTED
            p.decided_at = timezone.now()
            p.save(update_fields=["status", "decided_at"])
            g.refresh_status()
        return Response(ParticipationSerializer(p).data)

    @extend_schema(request=ReportCreateSerializer, responses={200: ReportResultSerializer})
    @action(detail=True, methods=["post"])
    def report(self, request, pk=None):
        gathering = self.get_object()
        if gathering.host_id == request.user.id:
            return Response({"detail": "내 모임은 신고할 수 없어요."}, status=400)
        s = ReportCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = report_content(gathering, request.user, **s.validated_data)
        return Response({"created": result.created, "hidden": result.hidden})
