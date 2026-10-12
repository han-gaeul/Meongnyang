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


@pytest.fixture
def auth_api(make_user):
    def _auth(user=None):
        user = user or make_user()
        client = APIClient()
        client.force_authenticate(user)
        client.user = user
        return client

    return _auth
