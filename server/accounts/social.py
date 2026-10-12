"""소셜 로그인 토큰 검증.

앱의 네이티브 SDK가 받은 토큰을 서버가 각 제공자에 직접 확인해 사용자 ID를 얻는다.
서버 리다이렉트 흐름이 없으므로 기존 웹의 state 미검증·open redirect 문제가 생기지 않는다.
"""

from dataclasses import dataclass

import requests
from django.conf import settings

TIMEOUT = 5


class SocialAuthError(Exception):
    pass


@dataclass(frozen=True)
class SocialProfile:
    uid: str
    email: str | None = None
    nickname: str | None = None


def _get_json(url: str, **kwargs) -> dict:
    try:
        resp = requests.get(url, timeout=TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise SocialAuthError("provider_unreachable") from exc
    if resp.status_code != 200:
        raise SocialAuthError("invalid_token")
    return resp.json()


def verify_kakao(access_token: str) -> SocialProfile:
    data = _get_json(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    account = data.get("kakao_account") or {}
    profile = account.get("profile") or {}
    return SocialProfile(
        uid=str(data["id"]),
        email=account.get("email"),
        nickname=profile.get("nickname"),
    )


def verify_naver(access_token: str) -> SocialProfile:
    data = _get_json(
        "https://openapi.naver.com/v1/nid/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if data.get("resultcode") != "00":
        raise SocialAuthError("invalid_token")
    r = data["response"]
    return SocialProfile(uid=r["id"], email=r.get("email"), nickname=r.get("nickname"))


def verify_google(id_token: str) -> SocialProfile:
    data = _get_json(
        "https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token}
    )
    if data.get("aud") not in settings.GOOGLE_CLIENT_IDS:
        raise SocialAuthError("audience_mismatch")
    return SocialProfile(uid=data["sub"], email=data.get("email"), nickname=data.get("name"))


def verify_apple(identity_token: str) -> SocialProfile:
    # TODO: Apple 공개키(JWKS)로 identity token 서명·aud·iss 검증
    raise SocialAuthError("not_implemented")


VERIFIERS = {
    "kakao": verify_kakao,
    "naver": verify_naver,
    "google": verify_google,
    "apple": verify_apple,
}
