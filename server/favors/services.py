"""부탁 자격과 돌봄 시트.

자격 (설계 문서 "신뢰 구조")
- 이웃(만남 1회 이상): 짧은 부탁을 서로 들어줄 수 있다.
- 단골 이웃(만남 3회 이상 + 둘 사이 짧은 부탁 완료 1회 이상): 방문형 부탁까지.
"""

from dataclasses import dataclass

from django.conf import settings
from django.db.models import Q

from meetups.services import meet_count

from .models import Favor


def completed_short_favors(user_id: int, other_id: int) -> int:
    """두 사람 사이(어느 쪽이 부탁했든) 완료된 짧은(비방문) 부탁 수"""
    return Favor.objects.filter(
        Q(requester_id=user_id, helper_id=other_id) | Q(requester_id=other_id, helper_id=user_id),
        status=Favor.Status.DONE,
        visit_home=False,
    ).count()


def completed_pairs(user_id: int) -> dict[int, int]:
    """나와 완료한 짧은 부탁 수를 상대별로"""
    rows = Favor.objects.filter(
        Q(requester_id=user_id) | Q(helper_id=user_id), status=Favor.Status.DONE, visit_home=False
    ).values_list("requester_id", "helper_id")
    out: dict[int, int] = {}
    for req, helper in rows:
        other = helper if req == user_id else req
        if other is not None:
            out[other] = out.get(other, 0) + 1
    return out


def level_of(meets: int, completed: int) -> str:
    if meets >= settings.REGULAR_NEIGHBOR_MEETS and completed >= 1:
        return "regular"
    if meets >= settings.NEIGHBOR_MEETS:
        return "neighbor"
    return "none"


@dataclass(frozen=True)
class Eligibility:
    ok: bool
    reason: str = ""


def can_help(user, favor: Favor) -> Eligibility:
    """user가 이 부탁을 맡을 수 있는가"""
    requester = favor.requester
    if user.id == requester.id:
        return Eligibility(False, "내 부탁이에요.")
    if user.blocks.filter(pk=requester.pk).exists() or requester.blocks.filter(pk=user.pk).exists():
        return Eligibility(False, "부탁을 맡을 수 없는 상대예요.")
    meets = meet_count(user.id, requester.id)
    if meets < settings.NEIGHBOR_MEETS:
        return Eligibility(False, "한 번 이상 만나 만남 인증을 한 이웃만 맡을 수 있어요.")
    if favor.visit_home:
        if level_of(meets, completed_short_favors(user.id, requester.id)) != "regular":
            return Eligibility(
                False,
                f"집에 방문하는 부탁은 {settings.REGULAR_NEIGHBOR_MEETS}번 이상 만나고 짧은 부탁을 한 번 함께 마친 단골 이웃만 맡을 수 있어요.",
            )
    return Eligibility(True)


# ---- 돌봄 시트 ----

def _journal_items(pet, days: int) -> dict:
    """최근 일기에서 식사·약·컨디션·산책·특이사항을 뽑는다.

    일기 기능(GPS 산책·건강 일기)이 들어오면 여기서 집계한다. 지금은 빈 값.
    """
    return {}


def draft_care_sheet(pet, days: int = 14) -> dict:
    sheet = {
        "meal": {"times_per_day": None, "amount": "", "food": ""},
        "meds": [],
        "condition": "",
        "walk": {"minutes": None, "per_week": None},
        "notes": "",
        "caution": "",
    }
    from_journal = _journal_items(pet, days)
    sheet.update(from_journal)
    return {
        **sheet,
        "basic": basic_info(pet),
        "source": {"days": days, "from_journal": sorted(from_journal)},
    }


def basic_info(pet) -> dict:
    """반려동물 프로필 스냅샷 (서버가 채운다, 사용자가 고치지 않음)"""
    return {
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed,
        "sex": pet.sex,
        "age": pet.age,
        "size": pet.size,
        "weight_kg": float(pet.weight_kg) if pet.weight_kg is not None else None,
        "neutered": pet.neutered,
        "vaccinated": pet.vaccinated,
        "traits": list(pet.traits or []),
    }


def care_summary(sheet: dict) -> dict:
    """목록·상세에서 누구나 보는 요약. 약·식사 같은 상세는 맡은 이웃에게만."""
    basic = sheet.get("basic") or {}
    return {
        "species": basic.get("species"),
        "breed": basic.get("breed", ""),
        "size": basic.get("size", ""),
        "age": basic.get("age"),
        "traits": basic.get("traits", []),
        "walk": sheet.get("walk") or {"minutes": None, "per_week": None},
    }
