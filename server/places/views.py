from django.db.models import Prefetch, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.pagination import DefaultCursorPagination
from common.permissions import IsVerifiedMember
from common.visibility import visible_to
from meetups.services import distance_m
from moderation.serializers import ReportCreateSerializer, ReportResultSerializer
from moderation.services import report_content
from pets.models import Pet

from . import services
from .models import Place, PlaceReview, ReviewImage
from .serializers import PlaceSerializer, PlaceSubmitSerializer, ReviewSerializer

DEFAULT_RADIUS, MAX_RADIUS = 3000, 20000
DUPLICATE_RADIUS_M = 100

CHIPS = ["large", "indoor", "floor", "nofee", "24h"]


def _float(params, key):
    try:
        return float(params[key])
    except (KeyError, ValueError):
        raise ValidationError({key: "숫자로 보내 주세요."})


class PlaceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """장소. 인증 전에도 지도·후기는 볼 수 있고, 제보·후기 작성은 인증 회원만."""

    serializer_class = PlaceSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in {"create"} or (self.action == "reviews" and self.request.method == "POST"):
            return [IsVerifiedMember()]
        return [IsAuthenticated()]

    def _reviews_qs(self):
        return visible_to(PlaceReview.objects.all(), self.request.user)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Place.objects.none()
        user = self.request.user
        return Place.objects.filter(
            Q(status=Place.Status.APPROVED) | Q(status=Place.Status.PENDING, created_by=user)
        ).prefetch_related(Prefetch("reviews", queryset=self._reviews_qs()))

    def _pet(self):
        pet_id = self.request.query_params.get("pet")
        if not pet_id:
            return None
        return Pet.objects.filter(pk=pet_id, user=self.request.user).first()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["pet"] = self._pet() if self.request else None
        return ctx

    @extend_schema(
        parameters=[
            OpenApiParameter("lat", float, required=True),
            OpenApiParameter("lng", float, required=True),
            OpenApiParameter("radius", int, description=f"m, 기본 {DEFAULT_RADIUS}, 최대 {MAX_RADIUS}"),
            OpenApiParameter("category", str, description="쉼표로 여러 개: cafe,restaurant"),
            OpenApiParameter("q", str, description="이름 검색"),
            OpenApiParameter("pet", int, description="내 반려동물 기준 적합도(fit) 계산"),
            OpenApiParameter("fit", str, enum=["1"], description="pet 기준 갈 수 있는 곳만"),
            OpenApiParameter("chips", str, description=f"쉼표로 여러 개: {','.join(CHIPS)}"),
        ],
        responses={200: PlaceSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        p = request.query_params
        lat, lng = _float(p, "lat"), _float(p, "lng")
        try:
            radius = min(max(int(p.get("radius", DEFAULT_RADIUS)), 100), MAX_RADIUS)
        except ValueError:
            radius = DEFAULT_RADIUS
        qs = self.get_queryset()
        if cats := [c for c in p.get("category", "").split(",") if c]:
            qs = qs.filter(category__in=cats)
        if q := p.get("q", "").strip():
            qs = qs.filter(name__icontains=q)

        rows = services.nearby(qs, lat, lng, radius, limit=300)
        ctx = self.get_serializer_context()
        ctx["distances"] = {pl.pk: d for pl, d in rows}
        s = PlaceSerializer(context=ctx)
        chips = {c for c in p.get("chips", "").split(",") if c in CHIPS}
        want_fit = p.get("fit") == "1" and ctx["pet"] is not None
        out = []
        for place, _ in rows:
            cond = s._cond(place)
            if chips and not services.matches_chips(cond, place, chips):
                continue
            if want_fit and services.fit_for(ctx["pet"], place, cond) != "yes":
                continue
            out.append(place)
            if len(out) >= 100:
                break
        return Response(PlaceSerializer(out, many=True, context=ctx).data)

    @extend_schema(request=PlaceSubmitSerializer, responses={201: PlaceSerializer})
    def create(self, request, *args, **kwargs):
        s = PlaceSubmitSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        name = d["name"].strip()
        lat0, lat1, lng0, lng1 = services.bbox(d["lat"], d["lng"], DUPLICATE_RADIUS_M)
        dup = next(
            (
                pl
                for pl in Place.objects.filter(
                    name__iexact=name, lat__range=(lat0, lat1), lng__range=(lng0, lng1)
                ).exclude(status=Place.Status.CLOSED)
                if distance_m(d["lat"], d["lng"], pl.lat, pl.lng) <= DUPLICATE_RADIUS_M
            ),
            None,
        )
        if dup:
            return Response({"detail": "이미 등록된 장소예요. 후기로 정보를 보태 주세요.", "id": dup.id}, status=409)
        place = s.save(name=name, created_by=request.user, source=Place.Source.USER, status=Place.Status.PENDING)
        return Response(PlaceSerializer(self.get_queryset().get(pk=place.pk), context=self.get_serializer_context()).data, status=201)

    @extend_schema(methods=["GET"], responses={200: ReviewSerializer(many=True)})
    @extend_schema(methods=["POST"], request=ReviewSerializer, responses={201: ReviewSerializer})
    @action(detail=True, methods=["get", "post"], pagination_class=DefaultCursorPagination)
    def reviews(self, request, pk=None):
        place = self.get_object()
        if request.method == "POST":
            if place.status != Place.Status.APPROVED:
                return Response({"detail": "운영자 확인 뒤에 후기를 남길 수 있어요."}, status=400)
            s = ReviewSerializer(data=request.data, context={"request": request})
            s.is_valid(raise_exception=True)
            review = s.save(place=place, user=request.user)
            return Response(ReviewSerializer(review, context={"request": request}).data, status=201)
        qs = self._reviews_qs().filter(place=place).select_related("user").prefetch_related(
            Prefetch("review_images", queryset=ReviewImage.objects.select_related("image"))
        )
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(ReviewSerializer(page, many=True, context={"request": request}).data)


class ReviewViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """후기 삭제(본인)·신고"""

    serializer_class = ReviewSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PlaceReview.objects.none()
        return visible_to(PlaceReview.objects.all(), self.request.user)

    def get_permissions(self):
        if self.action == "report":
            return [IsVerifiedMember()]
        return [IsAuthenticated()]

    def perform_destroy(self, instance):
        if instance.user_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("내 후기만 지울 수 있어요.")
        instance.delete()

    @extend_schema(request=ReportCreateSerializer, responses={200: ReportResultSerializer})
    @action(detail=True, methods=["post"])
    def report(self, request, pk=None):
        review = self.get_object()
        if review.user_id == request.user.id:
            return Response({"detail": "내 후기는 신고할 수 없어요."}, status=400)
        s = ReportCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = report_content(review, request.user, **s.validated_data)
        return Response({"created": result.created, "hidden": result.hidden})
