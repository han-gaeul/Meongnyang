import pytest

from accounts import social
from accounts.models import SocialAccount, User


@pytest.mark.django_db
def test_signup_then_login_returns_tokens(api):
    res = api.post(
        "/api/v1/auth/signup",
        {"email": "a@example.com", "password": "a-strong-pass-123", "nickname": "콩이맘"},
        format="json",
    )
    assert res.status_code == 201
    assert {"access", "refresh"} <= res.data.keys()

    res = api.post(
        "/api/v1/auth/login",
        {"email": "a@example.com", "password": "a-strong-pass-123"},
        format="json",
    )
    assert res.status_code == 200
    assert "access" in res.data


@pytest.mark.django_db
def test_signup_rejects_weak_password(api):
    res = api.post(
        "/api/v1/auth/signup",
        {"email": "a@example.com", "password": "1234", "nickname": "콩이맘"},
        format="json",
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_me_requires_login(api):
    assert api.get("/api/v1/me").status_code == 401


@pytest.mark.django_db
def test_me_cannot_self_verify_identity(auth_api):
    client = auth_api()
    res = client.patch("/api/v1/me", {"is_identity_verified": True}, format="json")
    assert res.status_code == 200
    client.user.refresh_from_db()
    assert client.user.is_identity_verified is False


@pytest.mark.django_db
def test_identity_verify_mock_success(auth_api):
    client = auth_api()
    res = client.post("/api/v1/auth/identity/verify", {"transaction_id": "mock-ok-p1"}, format="json")
    assert res.status_code == 200
    assert res.data["is_identity_verified"] is True
    # 응답에 실명·CI가 노출되지 않는다
    assert "legal_name" not in res.data and "ci_hash" not in res.data


@pytest.mark.django_db
def test_identity_verify_failure(auth_api):
    client = auth_api()
    res = client.post("/api/v1/auth/identity/verify", {"transaction_id": "bad"}, format="json")
    assert res.status_code == 400
    client.user.refresh_from_db()
    assert client.user.is_identity_verified is False


@pytest.mark.django_db
def test_same_person_cannot_verify_two_accounts(auth_api):
    first = auth_api()
    second = auth_api()
    assert first.post("/api/v1/auth/identity/verify", {"transaction_id": "mock-ok-same"}, format="json").status_code == 200
    # 거래 ID는 다르지만 같은 사람(같은 CI)
    res = second.post("/api/v1/auth/identity/verify", {"transaction_id": "mock-ok-same:2"}, format="json")
    assert res.status_code == 409
    second.user.refresh_from_db()
    assert second.user.is_identity_verified is False


@pytest.mark.django_db
def test_transaction_id_cannot_be_reused(auth_api):
    first = auth_api()
    second = auth_api()
    first.post("/api/v1/auth/identity/verify", {"transaction_id": "mock-ok-x"}, format="json")
    res = second.post("/api/v1/auth/identity/verify", {"transaction_id": "mock-ok-x"}, format="json")
    assert res.status_code == 409


@pytest.mark.django_db
def test_social_login_creates_user_without_password(api, monkeypatch):
    monkeypatch.setitem(
        social.VERIFIERS, "kakao", lambda token: social.SocialProfile(uid="k1", nickname="콩이아빠")
    )
    res = api.post("/api/v1/auth/social/kakao", {"token": "t"}, format="json")
    assert res.status_code == 200
    assert res.data["created"] is True
    user = SocialAccount.objects.get(provider="kakao", provider_uid="k1").user
    assert user.has_usable_password() is False

    # 두 번째 로그인은 같은 계정
    res = api.post("/api/v1/auth/social/kakao", {"token": "t"}, format="json")
    assert res.data["created"] is False
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_social_login_does_not_link_existing_email(api, make_user, monkeypatch):
    existing = make_user(email="taken@example.com")
    monkeypatch.setitem(
        social.VERIFIERS,
        "google",
        lambda token: social.SocialProfile(uid="g1", email="taken@example.com"),
    )
    res = api.post("/api/v1/auth/social/google", {"token": "t"}, format="json")
    assert res.status_code == 200
    linked = SocialAccount.objects.get(provider_uid="g1").user
    assert linked != existing


@pytest.mark.django_db
def test_social_login_invalid_token(api, monkeypatch):
    def bad(token):
        raise social.SocialAuthError("invalid_token")

    monkeypatch.setitem(social.VERIFIERS, "naver", bad)
    assert api.post("/api/v1/auth/social/naver", {"token": "t"}, format="json").status_code == 401


@pytest.mark.django_db
def test_unknown_provider(api):
    assert api.post("/api/v1/auth/social/facebook", {"token": "t"}, format="json").status_code == 404


@pytest.mark.django_db
def test_logout_blacklists_refresh(api):
    res = api.post(
        "/api/v1/auth/signup",
        {"email": "b@example.com", "password": "a-strong-pass-123", "nickname": "보리맘"},
        format="json",
    )
    access, refresh = res.data["access"], res.data["refresh"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert api.post("/api/v1/auth/logout", {"refresh": refresh}, format="json").status_code == 205
    api.credentials()
    res = api.post("/api/v1/auth/token/refresh", {"refresh": refresh}, format="json")
    assert res.status_code == 401
