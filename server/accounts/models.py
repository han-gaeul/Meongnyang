from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        email = self.normalize_email(email) if email else None
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            # 소셜 가입자는 비밀번호 로그인 불가 (기존 웹의 "공용 비밀번호" 문제 방지)
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    username = None
    first_name = None
    last_name = None

    # 소셜 가입자는 이메일이 없을 수 있음 (NULL은 unique 제약에서 제외)
    email = models.EmailField(unique=True, null=True, blank=True)
    nickname = models.CharField(max_length=20, unique=True)

    # 동네
    region_name = models.CharField(max_length=50, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # 휴대폰 본인인증 결과. CI 원문은 저장하지 않고 HMAC 해시만 보관.
    is_identity_verified = models.BooleanField(default=False)
    ci_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    # 반려동물 등록정보 조회(이름·생년월일 대조)에만 사용. API로 노출하지 않음.
    legal_name = models.CharField(max_length=50, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    followings = models.ManyToManyField(
        "self", symmetrical=False, related_name="followers", blank=True
    )
    blocks = models.ManyToManyField(
        "self", symmetrical=False, related_name="blocked_by", blank=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]

    objects = UserManager()

    def __str__(self):
        return self.nickname

    @property
    def is_verified_member(self) -> bool:
        return self.is_identity_verified and self.pets.filter(
            verification_status="approved"
        ).exists()


class SocialAccount(models.Model):
    class Provider(models.TextChoices):
        KAKAO = "kakao"
        NAVER = "naver"
        GOOGLE = "google"
        APPLE = "apple"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_accounts")
    provider = models.CharField(max_length=10, choices=Provider.choices)
    provider_uid = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_uid"], name="uniq_social_account"
            )
        ]


class IdentityVerification(models.Model):
    """본인인증 시도 기록. 대행사 거래 ID와 결과만 남긴다."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="identity_verifications")
    provider = models.CharField(max_length=20)
    transaction_id = models.CharField(max_length=100, unique=True)
    succeeded = models.BooleanField()
    failure_reason = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
