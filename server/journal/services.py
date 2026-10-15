"""일기 → 돌봄 시트 집계.

부탁 글을 쓸 때 최근 N일 일기에서 돌봄에 필요한 값만 뽑는다. 값이 없는 항목은 빼서
보호자가 직접 채우게 한다.
"""

from datetime import timedelta

from django.utils import timezone

from meetups.services import distance_m

from .models import JournalEntry

MAX_ROUTE_POINTS = 3000


def route_length_m(route: list) -> int:
    total = 0.0
    for (a_lat, a_lng), (b_lat, b_lng) in zip(route, route[1:]):
        total += distance_m(a_lat, a_lng, b_lat, b_lng)
    return round(total)


def simplify(route: list, min_step_m: float = 5) -> list:
    """GPS 떨림으로 생긴 촘촘한 점을 줄인다 (min_step_m보다 가까운 점은 버림)"""
    if len(route) <= 2:
        return route
    out = [route[0]]
    for pt in route[1:-1]:
        if distance_m(out[-1][0], out[-1][1], pt[0], pt[1]) >= min_step_m:
            out.append(pt)
    out.append(route[-1])
    return out


def _fmt_date(d) -> str:
    return f"{d.month}월 {d.day}일"


def care_sheet_items(pet, days: int) -> dict:
    since = timezone.localdate() - timedelta(days=days - 1)
    entries = list(JournalEntry.objects.filter(pet=pet, date__gte=since).order_by("-date", "-id"))
    out: dict = {}

    health = [e for e in entries if e.kind == JournalEntry.Kind.HEALTH]
    meal = next((e for e in health if e.meals_per_day is not None or e.food or e.meal_amount), None)
    if meal:
        out["meal"] = {"times_per_day": meal.meals_per_day, "amount": meal.meal_amount, "food": meal.food}

    # 가장 최근에 약을 기록한 건강 일기 기준 (빈 목록이면 '먹는 약 없음')
    meds = next((e for e in health if e.meds is not None), None)
    if meds and meds.meds:
        out["meds"] = [
            {"name": m.get("name", ""), "dose": m.get("dose", ""), "time": m.get("time", "")} for m in meds.meds
        ]

    vit = [e for e in health if e.vitality]
    if vit:
        avg = sum(e.vitality for e in vit) / len(vit)
        latest = vit[0]
        out["condition"] = f"활력 {latest.vitality}/5 ({_fmt_date(latest.date)} 기록, 최근 {days}일 평균 {avg:.1f})"

    walks = [e for e in entries if e.kind == JournalEntry.Kind.WALK and e.duration_sec]
    if walks:
        minutes = round(sum(e.duration_sec for e in walks) / len(walks) / 60)
        per_week = round(len(walks) * 7 / days)
        out["walk"] = {"minutes": minutes, "per_week": max(per_week, 1)}

    notes = [e for e in entries if e.share_in_care_sheet and e.content.strip()][:3]
    if notes:
        text = "\n".join(f"{_fmt_date(e.date)}: {e.content.strip()}" for e in notes)
        out["notes"] = text[:500]
    return out
