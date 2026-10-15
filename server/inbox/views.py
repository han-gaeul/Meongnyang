from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.pagination import DefaultCursorPagination
from common.permissions import IsVerifiedMember
from moderation.serializers import ReportCreateSerializer, ReportResultSerializer
from moderation.services import report_content
from notifications.models import Notification
from notifications.services import notify

from . import services
from .models import Message
from .serializers import CanSendSerializer, MessageSerializer, SendSerializer, ThreadSerializer, WithSerializer


class MessageViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """쪽지. 목록은 ?with=<상대 id>로 한 사람과 주고받은 쪽지(최신순)."""

    serializer_class = MessageSerializer
    pagination_class = DefaultCursorPagination

    def get_permissions(self):
        if self.action in {"create", "send"}:
            return [IsVerifiedMember()]
        return [IsAuthenticated()]

    def get_throttles(self):
        self.throttle_scope = "message" if self.action == "send" else None
        return super().get_throttles()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Message.objects.none()
        user = self.request.user
        return Message.objects.filter(
            Q(sender=user, sender_deleted=False) | Q(recipient=user, recipient_deleted=False)
        ).select_related("sender", "recipient")

    def _other(self, user_id):
        try:
            return get_user_model().objects.filter(pk=int(user_id)).first()
        except (TypeError, ValueError):
            raise ValidationError({"with": "상대 id를 숫자로 보내 주세요."})

    @extend_schema(parameters=[OpenApiParameter("with", int, required=True, description="상대 사용자 id")])
    def list(self, request, *args, **kwargs):
        other_id = request.query_params.get("with")
        if not other_id:
            raise ValidationError({"with": "상대를 정해 주세요."})
        qs = self.get_queryset().filter(Q(sender_id=other_id) | Q(recipient_id=other_id))
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @extend_schema(responses={200: ThreadSerializer(many=True)})
    @action(detail=False, methods=["get"], pagination_class=None)
    def threads(self, request):
        """쪽지함: 상대별 마지막 쪽지"""
        return Response(ThreadSerializer(services.threads(request.user), many=True, context={"request": request}).data)

    @extend_schema(parameters=[OpenApiParameter("to", int, required=True)], responses={200: CanSendSerializer})
    @action(detail=False, methods=["get"], url_path="can-send")
    def can_send(self, request):
        r = services.can_send(request.user, self._other(request.query_params.get("to")))
        return Response({"ok": r.ok, "reason": r.reason})

    @extend_schema(request=SendSerializer, responses={201: MessageSerializer})
    @action(detail=False, methods=["post"], url_path="send")
    def send(self, request):
        s = SendSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        recipient = self._other(s.validated_data["recipient"])
        r = services.can_send(request.user, recipient)
        if not r.ok:
            return Response({"detail": r.reason}, status=403)
        m = Message.objects.create(sender=request.user, recipient=recipient, content=s.validated_data["content"])
        notify(
            recipient,
            Notification.Kind.MESSAGE,
            f"{request.user.nickname}님의 쪽지",
            m.content[:80],
            path=f"/messages/{request.user.id}",
        )
        return Response(self.get_serializer(m).data, status=201)

    @extend_schema(request=WithSerializer, responses={204: None})
    @action(detail=False, methods=["post"])
    def read(self, request):
        """한 사람에게서 받은 쪽지를 모두 읽음으로"""
        s = WithSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        now = timezone.now()
        Message.objects.filter(recipient=request.user, sender_id=s.validated_data["user"], read_at__isnull=True).update(read_at=now)
        # 그 사람 쪽지 알림도 읽음 처리
        Notification.objects.filter(
            user=request.user, kind=Notification.Kind.MESSAGE, data__path=f"/messages/{s.validated_data['user']}", read_at__isnull=True
        ).update(read_at=now)
        return Response(status=204)

    def perform_destroy(self, m):
        """내 쪽에서만 지운다"""
        if m.sender_id == self.request.user.id:
            m.sender_deleted = True
        if m.recipient_id == self.request.user.id:
            m.recipient_deleted = True
        m.save(update_fields=["sender_deleted", "recipient_deleted"])

    @extend_schema(request=ReportCreateSerializer, responses={200: ReportResultSerializer})
    @action(detail=True, methods=["post"])
    def report(self, request, pk=None):
        """받은 쪽지 신고: 운영자 검토로 넘기고 내 쪽지함에서는 숨긴다"""
        m = self.get_object()
        if m.recipient_id != request.user.id:
            return Response({"detail": "받은 쪽지만 신고할 수 있어요."}, status=400)
        s = ReportCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = report_content(m, request.user, **s.validated_data)
        m.recipient_deleted = True
        m.save(update_fields=["recipient_deleted"])
        return Response({"created": result.created, "hidden": True})
