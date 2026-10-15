"""장소 검색과 동반 조건 계산.

반경 검색·거리순 정렬은 좌표 계산으로 한다(나중에 PostGIS로 바꿀 수 있게 여기 모아 둔다).
동반 조건은 '공식·제보 정책'과 '실제 방문 후기'를 합쳐 계산한다. 정책 확인 이후의
최신 후기가 있으면 후기를 우선한다.
"""

import math
from dataclasses import dataclass, field

from meetups.services import distance_m

from .models import Place, PlaceReview

DEG_LAT_M = 111_320  # 위도 1도 ≈ 111km


def bbox(lat: float, lng: float, radius_m: float) -> tuple[float, float, float, float]:
    dlat = radius_m / DEG_LAT_M
    dlng = radius_m / (DEG_LAT_M * max(math.cos(math.radians(lat)), 0.01))
    return lat - dlat, lat + dlat, lng - dlng, lng + dlng


def nearby(qs, lat: float, lng: float, radius_m: float, limit: int = 100) -> list[tuple[Place, float]]:
    """반경 안 장소를 가까운 순으로 (장소, 거리m)"""
    lat0, lat1, lng0, lng1 = bbox(lat, lng, radius_m)
    rows = []
    for p in qs.filter(lat__range=(lat0, lat1), lng__range=(lng0, lng1)):
        d = distance_m(lat, lng, p.lat, p.lng)
        if d <= radius_m:
            rows.append((p, d))
    rows.sort(key=lambda r: r[1])
    return rows[:limit]


@dataclass
class Conditions:
    """화면에 보여줄 동반 조건 요약. None은 '확인 안 됨'."""

    large_ok: bool | None = None
    space: str = ""
    floor_ok: bool | None = None
    extra_fee: bool | None = None
    review_count: int = 0
    large_reviews: int = 0  # 대형견이 함께 들어간 후기 수
    max_weight_admitted: float | None = None  # 후기 중 함께 들어간 가장 무거운 반려동물
    last_checked: object = None  # datetime
    differs_from_policy: bool = False  # 최신 후기가 밝힌 정책과 다름
    _admitted_weights: list = field(default_factory=list, repr=False)


def _newer(review: PlaceReview, place: Place) -> bool:
    return place.policy_checked_at is None or review.created_at > place.policy_checked_at


def conditions(place: Place, reviews: list[PlaceReview]) -> Conditions:
    """reviews: 숨김 제외, 최신순"""
    declared_large = None
    if place.sizes_allowed:
        declared_large = "L" in place.sizes_allowed
    declared_fee = None if place.fee_per_pet is None else place.fee_per_pet > 0
    c = Conditions(
        large_ok=declared_large,
        space=place.space,
        floor_ok=place.floor_ok,
        extra_fee=declared_fee,
        review_count=len(reviews),
        last_checked=place.policy_checked_at,
    )

    admitted = [r for r in reviews if r.admitted]
    c.large_reviews = sum(1 for r in admitted if r.pet_size == "L")
    weights = [float(r.pet_weight_kg) for r in admitted if r.pet_weight_kg is not None]
    c._admitted_weights = weights
    c.max_weight_admitted = max(weights) if weights else None
    if reviews and (c.last_checked is None or reviews[0].created_at > c.last_checked):
        c.last_checked = reviews[0].created_at

    # 후기가 정책보다 최신이면 후기를 따른다 (방문 확인 후기 우선)
    fresh = sorted(
        (r for r in reviews if _newer(r, place)), key=lambda r: (not r.verified_visit, -r.created_at.timestamp())
    )
    large_fresh = next((r for r in fresh if r.pet_size == "L"), None)
    if large_fresh is not None:
        c.large_ok = large_fresh.admitted
    elif c.large_ok is None and c.large_reviews:
        c.large_ok = True
    for attr, review_attr in (("space", "space"), ("floor_ok", "floor_ok"), ("extra_fee", "extra_fee")):
        r = next((r for r in fresh if getattr(r, review_attr) not in (None, "")), None)
        if r is not None:
            value = getattr(r, review_attr)
            declared = getattr(c, attr)
            if declared not in (None, "") and declared != value:
                c.differs_from_policy = True
            setattr(c, attr, value)
    if declared_large is not None and c.large_ok != declared_large:
        c.differs_from_policy = True
    return c


def fit_for(pet, place: Place, c: Conditions) -> str:
    """'yes' 갈 수 있음 / 'no' 어려움 / 'unknown' 확인 안 됨"""
    if pet is None:
        return "unknown"
    if place.category == Place.Category.STAY and pet.species == "cat" and place.cats_ok is not None:
        return "yes" if place.cats_ok else "no"
    weight = float(pet.weight_kg) if pet.weight_kg is not None else None
    # 비슷하거나 더 무거운 반려동물이 실제로 함께 들어간 후기
    if weight is not None and any(w >= weight for w in c._admitted_weights):
        return "yes"
    if pet.size == "L" and c.large_ok is not None:
        if not c.large_ok:
            return "no"
    if place.sizes_allowed and pet.size:
        if pet.size not in place.sizes_allowed:
            # 정책엔 없지만 최신 후기로 대형견 입장이 확인된 경우
            return "yes" if pet.size == "L" and c.large_ok is True else "no"
        if place.max_weight_kg and weight is not None and weight > place.max_weight_kg:
            return "no"
        return "yes"
    if pet.size == "L" and c.large_ok:
        return "yes"
    return "unknown"


def matches_chips(c: Conditions, place: Place, chips: set[str]) -> bool:
    if "large" in chips and c.large_ok is not True:
        return False
    if "indoor" in chips and c.space != Place.Space.INDOOR:
        return False
    if "floor" in chips and c.floor_ok is not True:
        return False
    if "nofee" in chips and c.extra_fee is not False:
        return False
    if "24h" in chips and not place.is_24h:
        return False
    return True


VISIT_RADIUS_M = 300


def is_visit(place: Place, lat: float | None, lng: float | None) -> bool:
    if lat is None or lng is None:
        return False
    return distance_m(lat, lng, place.lat, place.lng) <= VISIT_RADIUS_M


def kakao_links(place: Place) -> dict:
    """카카오맵 웹 링크 (앱이 설치돼 있으면 카카오맵 앱으로 열린다)"""
    from urllib.parse import quote

    name = quote(place.name)
    view = (
        f"https://place.map.kakao.com/{place.kakao_place_id}"
        if place.kakao_place_id
        else f"https://map.kakao.com/link/map/{name},{place.lat},{place.lng}"
    )
    return {"view": view, "directions": f"https://map.kakao.com/link/to/{name},{place.lat},{place.lng}"}
