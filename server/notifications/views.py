from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import DefaultCursorPagination

from .models import DeviceToken, Notification
from .serializers import DeviceTokenSerializer, NotificationSerializer, UnreadSerializer


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """내 알림 (최신순)"""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultCursorPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        self.get_queryset().filter(pk=pk, read_at__isnull=True).update(read_at=timezone.now())
        return Response(status=204)

    @extend_schema(request=None, responses={204: None})
    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response(status=204)


class UnreadView(APIView):
    """탭 배지용: 안 읽은 알림·쪽지 수"""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UnreadSerializer})
    def get(self, request):
        from inbox.models import Message

        return Response(
            {
                "notifications": Notification.objects.filter(user=request.user, read_at__isnull=True).count(),
                "messages": Message.objects.filter(
                    recipient=request.user, read_at__isnull=True, recipient_deleted=False
                ).count(),
            }
        )


class DeviceView(APIView):
    """푸시 토큰 등록·해제. 같은 토큰을 다른 계정이 쓰면 마지막 로그인 계정으로 옮긴다."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=DeviceTokenSerializer, responses={204: None})
    def post(self, request):
        s = DeviceTokenSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        DeviceToken.objects.update_or_create(
            token=s.validated_data["token"],
            defaults={"user": request.user, "platform": s.validated_data["platform"], "active": True},
        )
        return Response(status=204)

    @extend_schema(request=DeviceTokenSerializer, responses={204: None})
    def delete(self, request):
        """로그아웃할 때 이 기기 푸시 끄기"""
        token = request.data.get("token", "")
        DeviceToken.objects.filter(token=token, user=request.user).delete()
        return Response(status=204)
