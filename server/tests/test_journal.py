from datetime import timedelta

import pytest
from django.utils import timezone

from journal.models import JournalEntry
from pets.models import Pet


def pet_of(client):
    return Pet.objects.filter(user=client.user).first()


def today(offset=0):
    return (timezone.localdate() - timedelta(days=offset)).isoformat()


def post(client, **data):
    data.setdefault("pet_id", pet_of(client).id)
    data.setdefault("date", today())
    return client.post("/api/v1/journal", data, format="json")


# 망원한강공원 근처를 동쪽으로 약 100m씩 3번 (총 약 300m)
ROUTE = [[37.5556, 126.9019], [37.5556, 126.90303], [37.5556, 126.90416], [37.5556, 126.90529]]


@pytest.mark.django_db
def test_walk_entry_computes_distance_and_duration(auth_api):
    me = auth_api()
    Pet.objects.create(user=me.user, name="콩이", species="dog")
    start = timezone.now() - timedelta(minutes=40)
    res = post(
        me,
        kind="walk",
        started_at=start.isoformat(),
        ended_at=(start + timedelta(minutes=35)).isoformat(),
        route=ROUTE,
        distance_m=99999,  # 클라이언트 값은 무시하고 경로로 계산
    )
    assert res.status_code == 201, res.data
    assert res.data["duration_sec"] == 35 * 60
    assert 290 <= res.data["distance_m"] <= 310
    assert len(res.data["route"]) == 4

    bad = post(me, kind="walk", started_at=start.isoformat(), ended_at=(start - timedelta(minutes=1)).isoformat())
    assert bad.status_code == 400
    # 경로 없이 시간만 적는 산책도 된다
    assert post(me, kind="walk", duration_sec=1200).status_code == 201
    assert post(me, kind="walk").status_code == 400


@pytest.mark.django_db
def test_only_owner_sees_entries_and_own_pets_only(auth_api):
    me, other = auth_api(), auth_api()
    Pet.objects.create(user=me.user, name="콩이", species="dog")
    other_pet = Pet.objects.create(user=other.user, name="나비", species="cat")
    eid = post(me, kind="daily", content="공원에서 신나게 뛰었다").data["id"]

    assert post(me, kind="daily", content="x", pet_id=other_pet.id).status_code == 400
    assert other.get(f"/api/v1/journal/{eid}").status_code == 404
    assert other.get("/api/v1/journal").data["results"] == []
    assert other.patch(f"/api/v1/journal/{eid}", {"content": "남의 일기"}, format="json").status_code == 404
    assert post(me, kind="daily", content="미래", date=(timezone.localdate() + timedelta(days=1)).isoformat()).status_code == 400
    assert post(me, kind="daily", content="").status_code == 400
    assert me.patch(f"/api/v1/journal/{eid}", {"kind": "walk"}, format="json").status_code == 400


@pytest.mark.django_db
def test_health_entry_validation(auth_api):
    me = auth_api()
    Pet.objects.create(user=me.user, name="콩이", species="dog")
    assert post(me, kind="health").status_code == 400
    assert post(me, kind="health", vitality=6).status_code == 400
    assert post(me, kind="health", meds=[]).status_code == 201  # '먹는 약 없음'도 기록
    res = post(me, kind="health", meals_per_day=2, food="로얄캐닌", vitality=4, meds=[{"name": "심장사상충약", "time": "저녁"}])
    assert res.status_code == 201
    assert res.data["meds"] == [{"name": "심장사상충약", "dose": "", "time": "저녁"}]


@pytest.mark.django_db
def test_calendar_and_filters(auth_api):
    me = auth_api()
    pet = Pet.objects.create(user=me.user, name="콩이", species="dog")
    post(me, kind="walk", duration_sec=1800)
    post(me, kind="walk", duration_sec=600)
    post(me, kind="health", vitality=3)
    post(me, kind="daily", content="어제 일", date=today(1))

    month = timezone.localdate().strftime("%Y-%m")
    cal = me.get("/api/v1/journal/calendar", {"month": month, "pet": pet.id}).data
    by_date = {d["date"]: d for d in cal}
    assert by_date[today()]["kinds"] == ["walk", "health"]
    assert by_date[today()]["walk_minutes"] == 40
    assert by_date[today()]["count"] == 3
    assert me.get("/api/v1/journal/calendar").status_code == 400
    assert me.get("/api/v1/journal/calendar", {"month": "2026-13"}).status_code == 400

    assert len(me.get("/api/v1/journal", {"date": today()}).data["results"]) == 3
    assert len(me.get("/api/v1/journal", {"kind": "walk"}).data["results"]) == 2


@pytest.mark.django_db
def test_care_sheet_is_filled_from_recent_journal(member_api):
    me = member_api()
    pet = pet_of(me)
    # 14일 안의 기록
    post(me, kind="walk", duration_sec=40 * 60, date=today(1))
    post(me, kind="walk", duration_sec=20 * 60, date=today(3))
    post(me, kind="health", meals_per_day=2, meal_amount="1컵", food="로얄캐닌", vitality=3, date=today(5),
         meds=[{"name": "피부약", "dose": "1알", "time": "아침"}])
    post(me, kind="health", vitality=5, date=today(0))
    post(me, kind="daily", content="왼쪽 앞발을 핥아요", share_in_care_sheet=True, date=today(2))
    post(me, kind="daily", content="부탁엔 안 넣을 일기", date=today(2))
    # 14일 밖의 기록은 무시
    post(me, kind="health", food="옛날 사료", date=today(20))

    sheet = me.get(f"/api/v1/pets/{pet.id}/care-sheet?days=14").data
    assert sorted(sheet["source"]["from_journal"]) == ["condition", "meal", "meds", "notes", "walk"]
    assert sheet["meal"] == {"times_per_day": 2, "amount": "1컵", "food": "로얄캐닌"}
    assert sheet["meds"] == [{"name": "피부약", "dose": "1알", "time": "아침"}]
    assert sheet["walk"] == {"minutes": 30, "per_week": 1}
    assert sheet["condition"].startswith("활력 5/5")
    assert "평균 4.0" in sheet["condition"]
    assert "왼쪽 앞발" in sheet["notes"] and "안 넣을" not in sheet["notes"]

    # 최근 건강 일기에 '약 없음'을 기록하면 약은 비운다
    post(me, kind="health", meds=[], date=today(0))
    assert "meds" not in me.get(f"/api/v1/pets/{pet.id}/care-sheet").data["source"]["from_journal"]


@pytest.mark.django_db
def test_route_simplify_drops_jitter(auth_api):
    me = auth_api()
    Pet.objects.create(user=me.user, name="콩이", species="dog")
    jitter = [[37.5556 + i * 0.000001, 126.9019] for i in range(50)] + [ROUTE[-1]]
    res = post(me, kind="walk", duration_sec=600, route=jitter)
    assert len(res.data["route"]) < 10
    assert JournalEntry.objects.get(pk=res.data["id"]).route[0] == jitter[0]
