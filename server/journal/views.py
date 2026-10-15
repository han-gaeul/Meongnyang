import calendar
from collections import defaultdict
from datetime import date

from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.pagination import DefaultCursorPagination

from .models import JournalEntry, JournalImage
from .serializers import CalendarDaySerializer, JournalEntrySerializer


def _month(value: str) -> tuple[date, date]:
    try:
        y, m = (int(x) for x in value.split("-"))
        first = date(y, m, 1)
    except (ValueError, TypeError):
        raise ValidationError({"month": "2026-10 처럼 보내 주세요."})
    return first, date(y, m, calendar.monthrange(y, m)[1])


class JournalPagination(DefaultCursorPagination):
    ordering = ("-date", "-id")


class JournalViewSet(viewsets.ModelViewSet):
    """내 반려동물 일기. 본인 것만 보이고 고칠 수 있다."""

    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = JournalPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return JournalEntry.objects.none()
        qs = JournalEntry.objects.filter(user=self.request.user).prefetch_related(
            Prefetch("entry_images", queryset=JournalImage.objects.select_related("image"))
        )
        if self.action not in ("list", "calendar"):
            return qs
        p = self.request.query_params
        if pet := p.get("pet"):
            qs = qs.filter(pet_id=pet)
        if kind := p.get("kind"):
            qs = qs.filter(kind=kind)
        if d := p.get("date"):
            qs = qs.filter(date=d)
        if m := p.get("month"):
            first, last = _month(m)
            qs = qs.filter(date__range=(first, last))
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        parameters=[
            OpenApiParameter("pet", int),
            OpenApiParameter("kind", str, enum=[k for k, _ in JournalEntry.Kind.choices]),
            OpenApiParameter("date", str, description="YYYY-MM-DD"),
            OpenApiParameter("month", str, description="YYYY-MM"),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        parameters=[OpenApiParameter("month", str, required=True), OpenApiParameter("pet", int)],
        responses={200: CalendarDaySerializer(many=True)},
    )
    @action(detail=False, methods=["get"], pagination_class=None)
    def calendar(self, request):
        """달력용: 기록이 있는 날과 종류, 산책 시간 합계"""
        if not request.query_params.get("month"):
            raise ValidationError({"month": "2026-10 처럼 보내 주세요."})
        days: dict = defaultdict(lambda: {"kinds": set(), "walk_sec": 0, "count": 0})
        for e in self.get_queryset().only("date", "kind", "duration_sec"):
            d = days[e.date]
            d["kinds"].add(e.kind)
            d["count"] += 1
            if e.kind == JournalEntry.Kind.WALK:
                d["walk_sec"] += e.duration_sec or 0
        order = [k for k, _ in JournalEntry.Kind.choices]
        rows = [
            {
                "date": k,
                "kinds": sorted(v["kinds"], key=order.index),
                "walk_minutes": round(v["walk_sec"] / 60),
                "count": v["count"],
            }
            for k, v in sorted(days.items())
        ]
        return Response(CalendarDaySerializer(rows, many=True).data)
