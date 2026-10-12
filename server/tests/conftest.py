import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.models import User


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def make_user(db):
    counter = {"n": 0}

    def _make(**kwargs):
        counter["n"] += 1
        n = counter["n"]
        kwargs.setdefault("email", f"user{n}@example.com")
        kwargs.setdefault("nickname", f"이웃{n}")
        kwargs.setdefault("password", "a-strong-pass-123")
        return User.objects.create_user(**kwargs)

    return _make


@pytest.fixture(autouse=True)
def _media_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    # 테스트에서만 빠른 해시 사용 (실서비스는 기본 PBKDF2)
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def make_member(make_user):
    """본인인증 + 인증된 반려동물을 가진 회원(커뮤니티 쓰기 가능)."""
    from pets.models import Pet

    counter = {"n": 0}

    def _make(**kwargs):
        counter["n"] += 1
        user = make_user(**kwargs)
        user.is_identity_verified = True
        user.ci_hash = f"test-ci-{user.pk}"
        user.save()
        Pet.objects.create(
            user=user, name="콩이", species="dog", verification_status=Pet.Verification.APPROVED
        )
        return user

    return _make


@pytest.fixture
def member_api(auth_api, make_member):
    def _member(**kwargs):
        return auth_api(make_member(**kwargs))

    return _member


@pytest.fixture
def auth_api(make_user):
    def _auth(user=None):
        user = user or make_user()
        client = APIClient()
        client.force_authenticate(user)
        client.user = user
        return client

    return _auth
