"""휴대폰 본인인증 대행사 연동.

앱이 대행사(PortOne 등) 인증 창을 띄우고, 끝나면 거래 ID만 서버로 보낸다.
서버는 앱이 보낸 결과를 믿지 않고 대행사에 직접 조회해 검증한다.
계약 전에는 MockIdentityProvider로 개발한다.
"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import date

from django.conf import settings


@dataclass(frozen=True)
class IdentityResult:
    verified: bool
    ci: str = ""
    name: str = ""
    birth_date: date | None = None
    failure_reason: str = ""


class IdentityProvider:
    name = "base"

    def verify(self, transaction_id: str) -> IdentityResult:
        raise NotImplementedError


class MockIdentityProvider(IdentityProvider):
    """개발용. 'mock-ok-<사람>' 또는 'mock-ok-<사람>:<아무값>'은 성공, 그 외는 실패.

    같은 <사람>은 같은 CI로 취급해 중복 가입 방지를 시험할 수 있다.
    """

    name = "mock"

    def verify(self, transaction_id: str) -> IdentityResult:
        if not transaction_id.startswith("mock-ok-"):
            return IdentityResult(verified=False, failure_reason="mock_rejected")
        person = transaction_id.removeprefix("mock-ok-").split(":", 1)[0]
        return IdentityResult(
            verified=True,
            ci=f"mock-ci-{person}",
            name="홍길동",
            birth_date=date(1995, 1, 1),
        )


class PortOneIdentityProvider(IdentityProvider):
    name = "portone"

    def verify(self, transaction_id: str) -> IdentityResult:
        # TODO: 계약 후 PortOne 본인인증 조회 API로 구현
        raise NotImplementedError("PortOne 연동은 계약 후 구현")


_PROVIDERS = {p.name: p for p in (MockIdentityProvider, PortOneIdentityProvider)}


def get_identity_provider() -> IdentityProvider:
    return _PROVIDERS[settings.IDENTITY_PROVIDER]()


def hash_ci(ci: str) -> str:
    return hmac.new(
        settings.CI_HASH_SECRET.encode(), ci.encode(), hashlib.sha256
    ).hexdigest()
