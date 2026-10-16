from django.conf import settings
from django.db import models


class Notification(models.Model):
    """앱 안 알림 목록. 같은 내용을 푸시로도 보낸다(기기 토큰이 있을 때)."""

    class Kind(models.TextChoices):
        MESSAGE = "message", "쪽지"
        GATHERING_APPLIED = "gathering_applied", "모임 신청 받음"
        GATHERING_DECIDED = "gathering_decided", "모임 신청 결과"
        FAVOR_APPLIED = "favor_applied", "부탁 신청 받음"
        FAVOR_MATCHED = "favor_matched", "부탁 약속"
        FAVOR_WITHDRAWN = "favor_withdrawn", "부탁 약속 취소"
        FAVOR_REPORTED = "favor_reported", "부탁 다 했어요"
        FAVOR_DONE = "favor_done", "부탁 완료"
        FAVOR_THANKS = "favor_thanks", "감사 인사"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=100)
    body = models.CharField(max_length=200, blank=True)
    # 눌렀을 때 열 화면. 예: {"path": "/favors/3"}
    data = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["user", "read_at"])]


class DeviceToken(models.Model):
    """Expo 푸시 토큰. 한 사람이 기기 여러 대를 쓸 수 있다."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=200, unique=True)
    platform = models.CharField(max_length=10, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
