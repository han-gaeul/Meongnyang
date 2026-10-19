import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured


def _reload_settings(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import config.settings as s

    return importlib.reload(s)


@pytest.fixture(autouse=True)
def _restore_settings(monkeypatch):
    yield
    monkeypatch.undo()
    import config.settings as s

    importlib.reload(s)


def test_mock_providers_blocked_in_production_unless_beta(monkeypatch):
    with pytest.raises(ImproperlyConfigured):
        _reload_settings(monkeypatch, DEBUG="False", ALLOW_MOCK_PROVIDERS="False")
    # 베타 스위치를 켜도 초대 코드가 없으면 안 된다
    with pytest.raises(ImproperlyConfigured):
        _reload_settings(monkeypatch, DEBUG="False", ALLOW_MOCK_PROVIDERS="True", BETA_INVITE_CODE="short")
    s = _reload_settings(monkeypatch, DEBUG="False", ALLOW_MOCK_PROVIDERS="True", BETA_INVITE_CODE="dongne-2026-beta")
    assert s.INVITE_REQUIRED is True


@pytest.mark.django_db
def test_invite_code_required_when_set(api, settings):
    body = {"email": "new@example.com", "password": "a-strong-pass-123", "nickname": "새이웃"}
    assert api.get("/api/v1/auth/config").data == {"invite_required": False, "beta": True}

    settings.BETA_INVITE_CODE = "dongne-2026-beta"
    settings.INVITE_REQUIRED = True
    assert api.get("/api/v1/auth/config").data["invite_required"] is True
    res = api.post("/api/v1/auth/signup", body, format="json")
    assert res.status_code == 400 and "invite_code" in res.data
    assert api.post("/api/v1/auth/signup", {**body, "invite_code": "wrong"}, format="json").status_code == 400
    assert api.post("/api/v1/auth/signup", {**body, "invite_code": "dongne-2026-beta"}, format="json").status_code == 201


@pytest.mark.django_db
def test_social_signup_needs_invite_but_existing_login_does_not(api, settings):
    from unittest import mock

    from accounts.social import SocialProfile

    settings.BETA_INVITE_CODE = "dongne-2026-beta"
    settings.INVITE_REQUIRED = True
    profile = SocialProfile(uid="k-1", email=None, nickname="카카오유저")
    with mock.patch.dict("accounts.views.VERIFIERS", {"kakao": lambda token: profile}):
        assert api.post("/api/v1/auth/social/kakao", {"token": "t"}, format="json").status_code == 400
        ok = api.post("/api/v1/auth/social/kakao", {"token": "t", "invite_code": "dongne-2026-beta"}, format="json")
        assert ok.status_code == 200 and ok.data["created"] is True
        again = api.post("/api/v1/auth/social/kakao", {"token": "t"}, format="json")
        assert again.status_code == 200 and again.data["created"] is False


@pytest.mark.django_db
def test_healthz(api):
    res = api.get("/healthz")
    assert res.status_code == 200 and res.json() == {"ok": True}


@pytest.mark.django_db
def test_beta_page_links_to_update_channel(client):
    res = client.get("/beta")
    assert res.status_code == 200
    body = res.content.decode()
    assert "exps://u.expo.dev/b8bcdae6-6579-450b-806d-7adeb4d72d33?channel-name=beta&amp;runtime-version=exposdk%3A57.0.0" in body
    assert "초대 코드" in body
