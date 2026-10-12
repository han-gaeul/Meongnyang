from django.conf import settings
from django.db import models

from common.models import Moderated


class Favor(Moderated):
    """이웃에게 하는 무상 부탁.

    1차 출시는 짧은 부탁(2시간 이내)만. 만난 적 있는 이웃에게만 보이고,
    보호자 집에 들어가야 하는 방문형 부탁은 단골 이웃에게만 열린다.
    돌봄 시트는 올릴 때의 스냅샷을 저장해, 나중에 일기를 고쳐도 바뀌지 않는다.
    """

    class Kind(models.TextChoices):
        MEAL = "meal", "밥 주기"
        WALK = "walk", "산책"
        HOSPITAL = "hospital", "병원 동행"
        ETC = "etc", "기타"

    class Status(models.TextChoices):
        OPEN = "open", "찾는 중"
        MATCHED = "matched", "약속됨"
        DONE = "done", "완료"
        CANCELLED = "cancelled", "취소"

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favors")
    pet = models.ForeignKey("pets.Pet", on_delete=models.PROTECT, related_name="favors")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    visit_home = models.BooleanField(default=False, help_text="보호자 집에 들어가야 하는 부탁")
    region_name = models.CharField(max_length=50, blank=True, db_index=True)
    title = models.CharField(max_length=50)
    content = models.TextField(max_length=2000, blank=True)
    place_name = models.CharField(max_length=100, blank=True, help_text="만나는 곳. 방문형은 수락 후 따로 안내")
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField()
    care_sheet = models.JSONField(default=dict)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    helper = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="helped_favors"
    )
    # 책임 범위·사고 처리 원칙 동의 (명시적 확인 기록)
    requester_agreed_at = models.DateTimeField()
    matched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at", "id"]

    def __str__(self):
        return self.title


class FavorApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "신청"
        ACCEPTED = "accepted", "수락"
        REJECTED = "rejected", "거절"
        CANCELLED = "cancelled", "취소"

    favor = models.ForeignKey(Favor, on_delete=models.CASCADE, related_name="applications")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favor_applications")
    message = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    agreed_at = models.DateTimeField(help_text="책임 범위 동의 시각")
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [models.UniqueConstraint(fields=["favor", "user"], name="uniq_favor_application")]


class FavorThanks(models.Model):
    """부탁을 마친 뒤 보호자가 남기는 감사 후기. 1차는 포인트 대신 이것만 남긴다."""

    favor = models.OneToOneField(Favor, on_delete=models.CASCADE, related_name="thanks")
    message = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
