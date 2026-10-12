"""만남 인증.

1. A가 자기 위치로 짧게 유효한 서명 토큰을 받아 QR로 띄운다.
2. B가 같은 자리에서 QR을 찍고 자기 위치와 함께 보낸다.
3. 서버가 서명·만료·두 위치의 거리를 확인하고 두 사람의 만남을 기록한다.

여러 명이 한 QR을 찍을 수 있다(모임장이 띄우고 참여자들이 찍는 단체 산책).
"""

import math
from dataclasses import dataclass

from django.conf import settings
from django.core import signing
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

from .models import Meetup

QR_PREFIX = "meongnyang:meetup:"
_SALT = "meetups.token"


class MeetupError(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 사이 거리(m), 하버사인 공식"""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def issue_token(user, lat: float, lng: float, gathering_id: int | None = None) -> str:
    payload = {"u": user.id, "lat": round(lat, 6), "lng": round(lng, 6), "g": gathering_id}
    return QR_PREFIX + signing.dumps(payload, salt=_SALT, compress=True)


@dataclass(frozen=True)
class ConfirmResult:
    meetup: Meetup
    created: bool  # False면 오늘 이미 인증한 사이
    other_id: int


def confirm(scanner, qr: str, lat: float, lng: float) -> ConfirmResult:
    from django.contrib.auth import get_user_model

    from gatherings.models import Gathering

    if not qr.startswith(QR_PREFIX):
        raise MeetupError("멍냥동네 만남 QR이 아니에요.", "invalid")
    try:
        data = signing.loads(qr[len(QR_PREFIX):], salt=_SALT, max_age=settings.MEETUP_TOKEN_TTL)
    except signing.SignatureExpired:
        raise MeetupError("QR이 만료됐어요. 상대에게 새로 띄워 달라고 해 주세요.", "expired")
    except signing.BadSignature:
        raise MeetupError("멍냥동네 만남 QR이 아니에요.", "invalid")

    if data["u"] == scanner.id:
        raise MeetupError("내 QR은 찍을 수 없어요.", "self")
    other = get_user_model().objects.filter(pk=data["u"], is_active=True).first()
    if other is None:
        raise MeetupError("상대 계정을 찾을 수 없어요.", "invalid")
    if scanner.blocks.filter(pk=other.pk).exists() or other.blocks.filter(pk=scanner.pk).exists():
        raise MeetupError("만남을 인증할 수 없는 상대예요.", "blocked")
    if not other.is_verified_member:
        raise MeetupError("상대가 아직 인증 회원이 아니에요.", "unverified")

    dist = distance_m(data["lat"], data["lng"], lat, lng)
    if dist > settings.MEETUP_MAX_DISTANCE_M:
        raise MeetupError("두 사람의 위치가 너무 멀어요. 같은 자리에서 다시 시도해 주세요.", "too_far")

    gathering = None
    if data.get("g"):
        g = Gathering.objects.filter(pk=data["g"]).first()
        if g and g.is_member(scanner) and g.is_member(other):
            gathering = g

    a, b = sorted([scanner.id, other.id])
    today = timezone.localdate()
    try:
        with transaction.atomic():
            meetup = Meetup.objects.create(
                user_a_id=a, user_b_id=b, met_on=today, distance_m=round(dist), gathering=gathering
            )
        created = True
    except IntegrityError:
        meetup = Meetup.objects.get(user_a_id=a, user_b_id=b, met_on=today)
        created = False
    return ConfirmResult(meetup=meetup, created=created, other_id=other.id)


# ---- 이웃 단계 ----

def level_for(count: int) -> str:
    if count >= settings.REGULAR_NEIGHBOR_MEETS:
        return "regular"  # 단골 이웃
    if count >= settings.NEIGHBOR_MEETS:
        return "neighbor"  # 이웃
    return "none"


def meet_count(user_id: int, other_id: int) -> int:
    a, b = sorted([user_id, other_id])
    return Meetup.objects.filter(user_a_id=a, user_b_id=b).count()


def neighbors_of(user) -> list[dict]:
    """나와 만난 적 있는 사람별 만남 횟수·마지막 만남일"""
    rows = (
        Meetup.objects.filter(Q(user_a=user) | Q(user_b=user))
        .values("user_a", "user_b")
        .annotate(count=Count("id"), last_met_on=Max("met_on"))
    )
    stats: dict[int, dict] = {}
    for r in rows:
        other = r["user_b"] if r["user_a"] == user.id else r["user_a"]
        stats[other] = {"count": r["count"], "last_met_on": r["last_met_on"]}
    return [{"user_id": k, **v, "level": level_for(v["count"])} for k, v in stats.items()]
