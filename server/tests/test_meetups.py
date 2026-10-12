from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from meetups.models import Meetup
from meetups.services import distance_m

HERE = {"lat": 37.5556, "lng": 126.8946}  # 망원한강공원 부근
NEAR = {"lat": 37.5560, "lng": 126.8950}  # 약 50m
FAR = {"lat": 37.5650, "lng": 126.8946}  # 약 1km


def qr_of(client, **extra):
    res = client.post("/api/v1/meetups/token", {**HERE, **extra}, format="json")
    assert res.status_code == 200, res.data
    return res.data["qr"]


def test_distance_sanity():
    assert 40 < distance_m(HERE["lat"], HERE["lng"], NEAR["lat"], NEAR["lng"]) < 70
    assert 900 < distance_m(HERE["lat"], HERE["lng"], FAR["lat"], FAR["lng"]) < 1100


@pytest.mark.django_db
def test_confirm_creates_meetup_and_neighbor(member_api):
    a, b = member_api(), member_api()
    res = b.post("/api/v1/meetups/confirm", {"qr": qr_of(a), **NEAR}, format="json")
    assert res.status_code == 200
    assert res.data["created"] is True
    assert res.data["neighbor"]["id"] == a.user.id
    assert res.data["neighbor"]["meet_count"] == 1
    assert res.data["neighbor"]["level"] == "neighbor"

    # 양쪽 모두 이웃 목록에 서로가 보인다
    assert [n["id"] for n in a.get("/api/v1/neighbors").data] == [b.user.id]
    assert [n["id"] for n in b.get("/api/v1/neighbors").data] == [a.user.id]
    # 좌표는 저장하지 않는다
    m = Meetup.objects.get()
    assert not hasattr(m, "lat") and 40 < m.distance_m < 70


@pytest.mark.django_db
def test_same_pair_counts_once_per_day(member_api):
    a, b = member_api(), member_api()
    b.post("/api/v1/meetups/confirm", {"qr": qr_of(a), **NEAR}, format="json")
    res = a.post("/api/v1/meetups/confirm", {"qr": qr_of(b), **NEAR}, format="json")  # 반대 방향도 같은 쌍
    assert res.data["created"] is False
    assert Meetup.objects.count() == 1


@pytest.mark.django_db
def test_three_days_makes_regular_neighbor(member_api):
    a, b = member_api(), member_api()
    today = timezone.localdate()
    for days_ago in (2, 1):
        with mock.patch("meetups.services.timezone.localdate", return_value=today - timedelta(days=days_ago)):
            b.post("/api/v1/meetups/confirm", {"qr": qr_of(a), **NEAR}, format="json")
    res = b.post("/api/v1/meetups/confirm", {"qr": qr_of(a), **NEAR}, format="json")
    assert res.data["neighbor"]["meet_count"] == 3
    assert res.data["neighbor"]["level"] == "regular"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("case", "code"),
    [("self", "self"), ("far", "too_far"), ("garbage", "invalid"), ("tampered", "invalid")],
)
def test_confirm_rejections(member_api, case, code):
    a, b = member_api(), member_api()
    qr = qr_of(a)
    payload = {"qr": qr, **NEAR}
    client = b
    if case == "self":
        client = a
    elif case == "far":
        payload.update(FAR)
    elif case == "garbage":
        payload["qr"] = "https://example.com"
    elif case == "tampered":
        payload["qr"] = qr[:-3] + "abc"
    res = client.post("/api/v1/meetups/confirm", payload, format="json")
    assert res.status_code == 400
    assert res.data["code"] == code
    assert Meetup.objects.count() == 0


@pytest.mark.django_db
def test_expired_qr(settings, member_api):
    a, b = member_api(), member_api()
    qr = qr_of(a)
    settings.MEETUP_TOKEN_TTL = -1
    res = b.post("/api/v1/meetups/confirm", {"qr": qr, **NEAR}, format="json")
    assert res.data["code"] == "expired"


@pytest.mark.django_db
def test_blocked_pair_cannot_meet(member_api):
    a, b = member_api(), member_api()
    a.post(f"/api/v1/users/{b.user.id}/block")
    res = b.post("/api/v1/meetups/confirm", {"qr": qr_of(a), **NEAR}, format="json")
    assert res.data["code"] == "blocked"


@pytest.mark.django_db
def test_unverified_cannot_issue_or_confirm(auth_api, member_api):
    guest = auth_api()
    a = member_api()
    assert guest.post("/api/v1/meetups/token", HERE, format="json").status_code == 403
    assert guest.post("/api/v1/meetups/confirm", {"qr": qr_of(a), **NEAR}, format="json").status_code == 403


@pytest.mark.django_db
def test_gathering_recorded_only_when_both_are_members(member_api):
    host, a, outsider = member_api(), member_api(), member_api()
    gid = host.post(
        "/api/v1/gatherings",
        {"kind": "walk", "title": "산책", "place_name": "공원", "capacity": 3,
         "starts_at": (timezone.now() + timedelta(hours=1)).isoformat()},
        format="json",
    ).data["id"]
    a.post(f"/api/v1/gatherings/{gid}/apply", {}, format="json")
    pid = host.get(f"/api/v1/gatherings/{gid}/applications").data[0]["id"]
    host.post(f"/api/v1/gatherings/{gid}/applications/{pid}/accept")

    qr = qr_of(host, gathering=gid)
    a.post("/api/v1/meetups/confirm", {"qr": qr, **NEAR}, format="json")
    outsider.post("/api/v1/meetups/confirm", {"qr": qr, **NEAR}, format="json")
    by_user = {m.user_b_id if m.user_a_id == host.user.id else m.user_a_id: m for m in Meetup.objects.all()}
    assert by_user[a.user.id].gathering_id == gid
    assert by_user[outsider.user.id].gathering_id is None  # 모임 참여자가 아니면 모임 기록 없이 만남만
