from django.conf import settings
from django.db import models

from common.models import Moderated


class Gathering(Moderated):
    """동네 모임. 1차는 산책·나눔. (집사 모임·행사 동행은 같은 모델에 kind만 추가)"""

    class Kind(models.TextChoices):
        WALK = "walk", "산책"
        SHARE = "share", "나눔"

    class Species(models.TextChoices):
        ALL = "all", "모두"
        DOG = "dog", "강아지"
        CAT = "cat", "고양이"

    class Status(models.TextChoices):
        OPEN = "open", "모집 중"
        CLOSED = "closed", "마감"
        CANCELLED = "cancelled", "취소"

    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_gatherings")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    species = models.CharField(max_length=3, choices=Species.choices, default=Species.ALL)
    region_name = models.CharField(max_length=50, blank=True, db_index=True)
    title = models.CharField(max_length=50)
    content = models.TextField(max_length=2000, blank=True)
    place_name = models.CharField(max_length=100, help_text="만나는 곳 (예: 망원한강공원 2번 출입구)")
    starts_at = models.DateTimeField()
    # 모임장을 뺀 참여 인원. 나눔은 보통 1명.
    capacity = models.PositiveSmallIntegerField(default=3)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at", "id"]

    def __str__(self):
        return self.title

    def count_accepted(self) -> int:
        return self.participations.filter(status=Participation.Status.ACCEPTED).count()

    def refresh_status(self):
        """정원이 차면 마감, 자리가 나면 다시 모집 중. 취소된 모임은 그대로."""
        if self.status == self.Status.CANCELLED:
            return
        new = self.Status.CLOSED if self.count_accepted() >= self.capacity else self.Status.OPEN
        if new != self.status:
            self.status = new
            self.save(update_fields=["status", "updated_at"])

    def is_member(self, user) -> bool:
        """모임장 또는 수락된 참여자"""
        return self.host_id == user.id or self.participations.filter(
            user=user, status=Participation.Status.ACCEPTED
        ).exists()


class Participation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "신청"
        ACCEPTED = "accepted", "수락"
        REJECTED = "rejected", "거절"
        CANCELLED = "cancelled", "취소"

    gathering = models.ForeignKey(Gathering, on_delete=models.CASCADE, related_name="participations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="participations")
    pet = models.ForeignKey("pets.Pet", on_delete=models.SET_NULL, null=True, blank=True)
    message = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["gathering", "user"], name="uniq_participation")
        ]
