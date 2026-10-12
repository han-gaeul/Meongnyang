from datetime import date

from django.conf import settings
from django.db import models


class Pet(models.Model):
    class Species(models.TextChoices):
        DOG = "dog", "강아지"
        CAT = "cat", "고양이"

    class Sex(models.TextChoices):
        MALE = "M", "남아"
        FEMALE = "F", "여아"

    class Size(models.TextChoices):
        SMALL = "S", "소형"
        MEDIUM = "M", "중형"
        LARGE = "L", "대형"

    class Verification(models.TextChoices):
        UNVERIFIED = "unverified", "미인증"
        PENDING = "pending", "검토 대기"  # 등록정보 조회 불가 → 운영자 검토
        APPROVED = "approved", "인증 완료"
        REJECTED = "rejected", "반려"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pets")
    name = models.CharField(max_length=25)
    species = models.CharField(max_length=3, choices=Species.choices)
    breed = models.CharField(max_length=40, blank=True)
    sex = models.CharField(max_length=1, choices=Sex.choices, blank=True)
    birthday = models.DateField(null=True, blank=True)
    neutered = models.BooleanField(null=True, blank=True)
    vaccinated = models.BooleanField(null=True, blank=True)
    # 동반 장소 필터("우리 아이가 갈 수 있는 곳")에 사용
    size = models.CharField(max_length=1, choices=Size.choices, blank=True)
    weight_kg = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    traits = models.JSONField(default=list, blank=True)  # 성격 태그

    registration_number = models.CharField(max_length=15, blank=True)
    verification_status = models.CharField(
        max_length=10, choices=Verification.choices, default=Verification.UNVERIFIED
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def age(self) -> int | None:
        if not self.birthday:
            return None
        today = date.today()
        years = today.year - self.birthday.year
        if (today.month, today.day) < (self.birthday.month, self.birthday.day):
            years -= 1
        return max(years, 0)
