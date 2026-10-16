from datetime import timedelta

from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import DefaultCursorPagination
from common.permissions import IsOwnerOrReadOnly, IsVerifiedMember
from common.visibility import visible_to
from meetups.models import Meetup
from moderation.serializers import ReportCreateSerializer, ReportResultSerializer
from moderation.services import report_content
from pets.models import Pet

from notifications.models import Notification as N
from notifications.services import notify

from . import services
from .models import Favor, FavorApplication, FavorThanks
from .serializers import (
    CareSheetDraftSerializer,
    FavorApplicationSerializer,
    FavorApplySerializer,
    FavorSerializer,
    FavorThanksCreateSerializer,
)

# 시작 시간이 이만큼 지나도 약속이 안 잡혔으면 목록에서 내린다
LIST_GRACE = timedelta(hours=1)


def neighbor_ids(user) -> set[int]:
    """만남 인증을 한 번이라도 한 상대"""
    pairs = Meetup.objects.filter(Q(user_a=user) | Q(user_b=user)).values_list("user_a_id", "user_b_id")
    return {b if a == user.id else a for a, b in pairs}


class UpcomingPagination(DefaultCursorPagination):
    ordering = ("starts_at", "id")


class FavorViewSet(viewsets.ModelViewSet):
    """이웃 부탁. 만난 적 있는 이웃의 부탁만 보인다."""

    serializer_class = FavorSerializer
    pagination_class = UpcomingPagination
    owner_field = "requester"

    def get_permissions(self):
        if self.action in {"create", "apply", "withdraw", "report", "finish"}:
            return [IsVerifiedMember()]
        if self.action in {"update", "partial_update", "destroy", "applications", "decide", "complete", "thank"}:
            return [IsOwnerOrReadOnly()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Favor.objects.none()
        user = self.request.user
        qs = (
            visible_to(Favor.objects.all(), user, author_field="requester")
            .filter(Q(requester=user) | Q(helper=user) | Q(requester_id__in=neighbor_ids(user)))
            .select_related("requester", "helper", "pet", "thanks")
            .prefetch_related(Prefetch("applications", queryset=FavorApplication.objects.select_related("user")))
        )
        if self.action != "list":
            return qs
        p = self.request.query_params
        if kind := p.get("kind"):
            qs = qs.filter(kind=kind)
        if p.get("mine") == "1":
            return qs.filter(Q(requester=user) | Q(applications__user=user)).distinct()
        # 이웃 부탁 목록: 아직 사람을 찾는 중이고, 내가 올린 건 뺀다
        return qs.filter(status=Favor.Status.OPEN, starts_at__gte=timezone.now() - LIST_GRACE).exclude(requester=user)

    @extend_schema(
        parameters=[
            OpenApiParameter("kind", str, enum=[k for k, _ in Favor.Kind.choices]),
            OpenApiParameter("mine", str, enum=["1"], description="내가 올렸거나 신청한 부탁(지난 것 포함)"),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def _fresh(self, pk):
        return self.get_queryset().get(pk=pk)

    def _ok(self, favor, status=200):
        return Response(self.get_serializer(self._fresh(favor.pk)).data, status=status)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        favor = s.save(requester=request.user, region_name=request.user.region_name)
        return self._ok(favor, status=201)

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return self._ok(Favor.objects.get(pk=kwargs["pk"]))

    def perform_destroy(self, instance):
        if instance.status == Favor.Status.DONE:
            return  # 완료된 부탁은 기록으로 남긴다
        if instance.applications.exists():
            instance.status = Favor.Status.CANCELLED
            instance.save(update_fields=["status", "updated_at"])
        else:
            instance.delete()

    # ---- 맡는 쪽 ----

    @extend_schema(request=FavorApplySerializer, responses={200: FavorSerializer})
    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        """맡겠다고 신청 (책임 범위 동의 필수)"""
        favor = self.get_object()
        if favor.status != Favor.Status.OPEN or favor.starts_at < timezone.now():
            return Response({"detail": "이미 약속이 잡혔거나 지난 부탁이에요."}, status=400)
        elig = services.can_help(request.user, favor)
        if not elig.ok:
            return Response({"detail": elig.reason}, status=403)
        s = FavorApplySerializer(data=request.data)
        s.is_valid(raise_exception=True)

        existing = FavorApplication.objects.filter(favor=favor, user=request.user).first()
        if existing and existing.status in ("pending", "accepted"):
            return Response({"detail": "이미 신청했어요."}, status=409)
        if existing and existing.status == "rejected":
            return Response({"detail": "보호자가 다른 이웃과 약속한 부탁이에요."}, status=400)
        FavorApplication.objects.update_or_create(
            favor=favor,
            user=request.user,
            defaults={
                "message": s.validated_data["message"],
                "status": FavorApplication.Status.PENDING,
                "agreed_at": timezone.now(),
                "decided_at": None,
            },
        )
        notify(favor.requester, N.Kind.FAVOR_APPLIED, f"{request.user.nickname}님이 부탁을 맡겠대요",
               favor.title, path=f"/favors/{favor.id}")
        return self._ok(favor)

    @extend_schema(request=None, responses={200: FavorSerializer})
    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        """신청 취소. 약속이 잡힌 뒤 취소하면 부탁은 다시 '찾는 중'이 된다."""
        favor = self.get_object()
        with transaction.atomic():
            f = Favor.objects.select_for_update().get(pk=favor.pk)
            a = FavorApplication.objects.filter(favor=f, user=request.user, status__in=["pending", "accepted"]).first()
            if a is None or f.status == Favor.Status.DONE:
                return Response({"detail": "취소할 신청이 없어요."}, status=400)
            a.status = FavorApplication.Status.CANCELLED
            a.save(update_fields=["status"])
            if f.helper_id == request.user.id and f.status == Favor.Status.MATCHED:
                f.helper = None
                f.matched_at = None
                f.helper_reported_at = None
                f.status = Favor.Status.OPEN
                f.save(update_fields=["helper", "matched_at", "helper_reported_at", "status", "updated_at"])
                notify(f.requester, N.Kind.FAVOR_WITHDRAWN, f"{request.user.nickname}님이 약속을 취소했어요",
                       f"'{f.title}' 부탁을 맡을 이웃을 다시 찾고 있어요.", path=f"/favors/{f.id}")
        return self._ok(favor)

    # ---- 부탁한 쪽 ----

    @extend_schema(responses={200: FavorApplicationSerializer(many=True)})
    @action(detail=True, methods=["get"], pagination_class=None)
    def applications(self, request, pk=None):
        favor = self.get_object()
        if favor.requester_id != request.user.id:
            return Response({"detail": "부탁한 사람만 볼 수 있어요."}, status=403)
        qs = favor.applications.select_related("user").exclude(status="cancelled")
        return Response(FavorApplicationSerializer(qs, many=True).data)

    @extend_schema(
        request=None,
        parameters=[OpenApiParameter("decision", str, location="path", enum=["accept", "reject"])],
        responses={200: FavorSerializer},
    )
    @action(detail=True, methods=["post"], url_path=r"applications/(?P<aid>\d+)/(?P<decision>accept|reject)")
    def decide(self, request, pk=None, aid=None, decision=None):
        """신청 수락(한 명과 약속)·거절"""
        favor = self.get_object()
        if favor.requester_id != request.user.id:
            return Response({"detail": "부탁한 사람만 할 수 있어요."}, status=403)
        with transaction.atomic():
            f = Favor.objects.select_for_update().select_related("requester").get(pk=favor.pk)
            a = FavorApplication.objects.select_related("user").filter(pk=aid, favor=f).first()
            if a is None or a.status != FavorApplication.Status.PENDING:
                return Response({"detail": "처리할 수 없는 신청이에요."}, status=400)
            now = timezone.now()
            if decision == "accept":
                if f.status != Favor.Status.OPEN:
                    return Response({"detail": "이미 다른 이웃과 약속했거나 끝난 부탁이에요."}, status=400)
                elig = services.can_help(a.user, f)  # 그 사이 차단 등 확인
                if not elig.ok:
                    return Response({"detail": elig.reason}, status=400)
                a.status = FavorApplication.Status.ACCEPTED
                f.status = Favor.Status.MATCHED
                f.helper = a.user
                f.matched_at = now
                f.save(update_fields=["status", "helper", "matched_at", "updated_at"])
            else:
                a.status = FavorApplication.Status.REJECTED
            a.decided_at = now
            a.save(update_fields=["status", "decided_at"])
        if decision == "accept":
            notify(a.user, N.Kind.FAVOR_MATCHED, f"{f.requester.nickname}님이 부탁했어요",
                   f"'{f.title}' 약속이 잡혔어요. 돌봄 시트를 확인해 주세요.", path=f"/favors/{f.id}")
        return self._ok(favor)

    @extend_schema(request=None, responses={200: FavorSerializer})
    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        """맡은 이웃: '다 했어요'. 보호자가 확인하면 완료된다."""
        favor = self.get_object()
        if favor.helper_id != request.user.id or favor.status != Favor.Status.MATCHED:
            return Response({"detail": "내가 맡은 진행 중인 부탁만 알릴 수 있어요."}, status=400)
        if favor.starts_at > timezone.now():
            return Response({"detail": "부탁 시간이 된 뒤에 알릴 수 있어요."}, status=400)
        if not favor.helper_reported_at:
            favor.helper_reported_at = timezone.now()
            favor.save(update_fields=["helper_reported_at", "updated_at"])
            notify(favor.requester, N.Kind.FAVOR_REPORTED, f"{request.user.nickname}님이 다 했다고 알렸어요",
                   "확인하면 부탁이 완료돼요.", path=f"/favors/{favor.id}")
        return self._ok(favor)

    @extend_schema(request=None, responses={200: FavorSerializer})
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """보호자: '확인했어요'. 이웃이 다 했다고 알렸거나 약속 시간이 끝난 뒤에 완료로 기록된다."""
        favor = self.get_object()
        if favor.status != Favor.Status.MATCHED:
            return Response({"detail": "약속이 잡힌 부탁만 완료할 수 있어요."}, status=400)
        if not services.can_confirm(favor):
            return Response({"detail": "이웃이 '다 했어요'를 누르거나 약속 시간이 끝나면 확인할 수 있어요."}, status=400)
        favor.status = Favor.Status.DONE
        favor.completed_at = timezone.now()
        favor.save(update_fields=["status", "completed_at", "updated_at"])
        if favor.helper:
            notify(favor.helper, N.Kind.FAVOR_DONE, "부탁을 잘 마쳤어요",
                   f"{request.user.nickname}님이 확인했어요. 고마워요!", path=f"/favors/{favor.id}")
        return self._ok(favor)

    @extend_schema(request=FavorThanksCreateSerializer, responses={200: FavorSerializer})
    @action(detail=True, methods=["post"])
    def thank(self, request, pk=None):
        """감사 후기 (완료 후 한 번)"""
        favor = self.get_object()
        if favor.status != Favor.Status.DONE:
            return Response({"detail": "완료한 부탁에만 남길 수 있어요."}, status=400)
        if FavorThanks.objects.filter(favor=favor).exists():
            return Response({"detail": "이미 감사 인사를 남겼어요."}, status=409)
        s = FavorThanksCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        FavorThanks.objects.create(favor=favor, message=s.validated_data["message"])
        if favor.helper:
            notify(favor.helper, N.Kind.FAVOR_THANKS, f"{request.user.nickname}님의 감사 인사",
                   s.validated_data["message"][:80], path=f"/favors/{favor.id}")
        return self._ok(favor)

    @extend_schema(request=ReportCreateSerializer, responses={200: ReportResultSerializer})
    @action(detail=True, methods=["post"])
    def report(self, request, pk=None):
        favor = self.get_object()
        if favor.requester_id == request.user.id:
            return Response({"detail": "내 부탁은 신고할 수 없어요."}, status=400)
        s = ReportCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = report_content(favor, request.user, **s.validated_data)
        return Response({"created": result.created, "hidden": result.hidden})


class CareSheetDraftView(APIView):
    """돌봄 시트 초안. 최근 일기(기본 14일)와 반려동물 프로필로 미리 채운다."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("days", int, description="일기 집계 기간(1~90일, 기본 14)")],
        responses={200: CareSheetDraftSerializer},
    )
    def get(self, request, pk):
        pet = get_object_or_404(Pet, pk=pk, user=request.user)
        try:
            days = min(max(int(request.query_params.get("days", 14)), 1), 90)
        except ValueError:
            days = 14
        return Response(services.draft_care_sheet(pet, days))
