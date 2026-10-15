"""반려동물 일기. 보호자 본인만 본다.

- 일반: 글·사진. '돌봄 시트에 넣기'를 켜면 부탁할 때 최근 특이사항으로 들어간다.
- 산책: GPS로 기록한 경로·시간·거리. 경로는 집 위치가 드러날 수 있어 본인에게만 보인다.
- 건강: 식사·활력·약·체중을 자유 글이 아닌 필드로 저장 → 돌봄 시트 자동 작성에 쓴다.
"""

from django.conf import settings
from django.db import models


class JournalEntry(models.Model):
    class Kind(models.TextChoices):
        DAILY = "daily", "일반"
        WALK = "walk", "산책"
        HEALTH = "health", "건강"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="journal_entries")
    pet = models.ForeignKey("pets.Pet", on_delete=models.CASCADE, related_name="journal_entries")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    date = models.DateField(db_index=True)
    title = models.CharField(max_length=50, blank=True)
    content = models.TextField(max_length=3000, blank=True)
    share_in_care_sheet = models.BooleanField(default=False, help_text="부탁할 때 돌봄 시트 '최근 특이사항'에 넣기")

    # 산책
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_sec = models.PositiveIntegerField(null=True, blank=True)
    distance_m = models.PositiveIntegerField(null=True, blank=True)
    route = models.JSONField(default=list, blank=True, help_text="[[lat, lng], ...] (본인만 열람)")

    # 건강
    meals_per_day = models.PositiveSmallIntegerField(null=True, blank=True)
    meal_amount = models.CharField(max_length=50, blank=True)
    food = models.CharField(max_length=50, blank=True)
    vitality = models.PositiveSmallIntegerField(null=True, blank=True, help_text="1~5")
    # None = 이번엔 기록 안 함, [] = 먹는 약 없음
    meds = models.JSONField(null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["pet", "kind", "date"])]
        verbose_name_plural = "journal entries"

    def __str__(self):
        return f"{self.pet} {self.date} {self.get_kind_display()}"


class JournalImage(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="entry_images")
    image = models.OneToOneField("uploads.UploadedImage", on_delete=models.CASCADE, related_name="journal_image")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
