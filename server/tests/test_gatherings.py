from datetime import timedelta

import pytest
from django.utils import timezone

from gatherings.models import Gathering, Participation


def walk(**overrides):
    data = {
        "kind": "walk",
        "species": "dog",
        "title": "저녁 한강 산책",
        "content": "대형견 환영",
        "place_name": "망원한강공원 2번 출입구",
        "starts_at": (timezone.now() + timedelta(days=1)).isoformat(),
        "capacity": 2,
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_unverified_can_browse_but_not_create_or_apply(auth_api, member_api):
    host = member_api()
    gid = host.post("/api/v1/gatherings", walk(), format="json").data["id"]
    guest = auth_api()
    assert guest.get("/api/v1/gatherings").status_code == 200
    assert guest.post("/api/v1/gatherings", walk(), format="json").status_code == 403
    assert guest.post(f"/api/v1/gatherings/{gid}/apply", {}, format="json").status_code == 403


@pytest.mark.django_db
def test_create_rejects_past_time(member_api):
    host = member_api()
    res = host.post("/api/v1/gatherings", walk(starts_at=(timezone.now() - timedelta(hours=1)).isoformat()), format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_apply_accept_until_full_then_closed(member_api):
    host = member_api()
    a, b, c = member_api(), member_api(), member_api()
    gid = host.post("/api/v1/gatherings", walk(capacity=2), format="json").data["id"]

    assert host.post(f"/api/v1/gatherings/{gid}/apply", {}, format="json").status_code == 400  # 내 모임
    for client in (a, b, c):
        assert client.post(f"/api/v1/gatherings/{gid}/apply", {"message": "같이 가요"}, format="json").status_code == 200
    assert a.post(f"/api/v1/gatherings/{gid}/apply", {}, format="json").status_code == 409  # 중복 신청

    apps = host.get(f"/api/v1/gatherings/{gid}/applications").data
    assert len(apps) == 3
    ids = {x["user"]["id"]: x["id"] for x in apps}

    # 신청자는 신청 목록을 볼 수 없다
    assert a.get(f"/api/v1/gatherings/{gid}/applications").status_code == 403
    # 다른 사람은 수락할 수 없다
    assert a.post(f"/api/v1/gatherings/{gid}/applications/{ids[b.user.id]}/accept").status_code == 403

    assert host.post(f"/api/v1/gatherings/{gid}/applications/{ids[a.user.id]}/accept").status_code == 200
    assert host.post(f"/api/v1/gatherings/{gid}/applications/{ids[b.user.id]}/accept").status_code == 200
    g = host.get(f"/api/v1/gatherings/{gid}").data
    assert g["status"] == "closed" and g["accepted_count"] == 2
    assert {p["user"]["id"] for p in g["participants"]} == {a.user.id, b.user.id}

    # 정원 초과 수락 불가
    assert host.post(f"/api/v1/gatherings/{gid}/applications/{ids[c.user.id]}/accept").status_code == 400

    # 한 명이 취소하면 다시 모집 중
    res = a.post(f"/api/v1/gatherings/{gid}/cancel")
    assert res.data["status"] == "open" and res.data["accepted_count"] == 1
    assert host.post(f"/api/v1/gatherings/{gid}/applications/{ids[c.user.id]}/accept").status_code == 200


@pytest.mark.django_db
def test_rejected_cannot_reapply_but_cancelled_can(member_api):
    host = member_api()
    a, b = member_api(), member_api()
    gid = host.post("/api/v1/gatherings", walk(capacity=3), format="json").data["id"]
    a.post(f"/api/v1/gatherings/{gid}/apply", {}, format="json")
    b.post(f"/api/v1/gatherings/{gid}/apply", {}, format="json")
    pa = Participation.objects.get(user=a.user).id
    host.post(f"/api/v1/gatherings/{gid}/applications/{pa}/reject")
    assert a.post(f"/api/v1/gatherings/{gid}/apply", {}, format="json").status_code == 400

    b.post(f"/api/v1/gatherings/{gid}/cancel")
    assert b.post(f"/api/v1/gatherings/{gid}/apply", {}, format="json").status_code == 200


@pytest.mark.django_db
def test_apply_with_my_pet_only(member_api):
    host = member_api()
    a, other = member_api(), member_api()
    gid = host.post("/api/v1/gatherings", walk(), format="json").data["id"]
    their_pet = other.user.pets.first().id
    assert a.post(f"/api/v1/gatherings/{gid}/apply", {"pet": their_pet}, format="json").status_code == 400
    res = a.post(f"/api/v1/gatherings/{gid}/apply", {"pet": a.user.pets.first().id}, format="json")
    assert res.status_code == 200
    assert res.data["my_participation"]["pet"]["name"] == "콩이"


@pytest.mark.django_db
def test_only_host_edits_and_status_is_automatic(member_api):
    host = member_api()
    other = member_api()
    gid = host.post("/api/v1/gatherings", walk(), format="json").data["id"]
    assert other.patch(f"/api/v1/gatherings/{gid}", {"title": "x"}, format="json").status_code == 403
    assert host.patch(f"/api/v1/gatherings/{gid}", {"status": "closed"}, format="json").status_code == 400
    assert host.patch(f"/api/v1/gatherings/{gid}", {"status": "cancelled"}, format="json").data["status"] == "cancelled"


@pytest.mark.django_db
def test_delete_with_participants_becomes_cancel(member_api):
    host = member_api()
    a = member_api()
    gid = host.post("/api/v1/gatherings", walk(), format="json").data["id"]
    a.post(f"/api/v1/gatherings/{gid}/apply", {}, format="json")
    assert host.delete(f"/api/v1/gatherings/{gid}").status_code == 204
    assert Gathering.objects.get(pk=gid).status == "cancelled"
    # 신청자도 내 모임 목록에서 취소된 모임을 볼 수 있다
    mine = a.get("/api/v1/gatherings?mine=1").data["results"]
    assert [g["status"] for g in mine] == ["cancelled"]


@pytest.mark.django_db
def test_list_filters_and_order(member_api):
    host = member_api()
    host.post("/api/v1/gatherings", walk(title="내일", starts_at=(timezone.now() + timedelta(days=1)).isoformat()), format="json")
    host.post("/api/v1/gatherings", walk(title="오늘", starts_at=(timezone.now() + timedelta(hours=2)).isoformat()), format="json")
    host.post("/api/v1/gatherings", walk(kind="share", species="cat", title="모래 나눔"), format="json")
    titles = lambda res: [g["title"] for g in res.data["results"]]  # noqa: E731
    assert titles(host.get("/api/v1/gatherings?kind=walk")) == ["오늘", "내일"]
    assert titles(host.get("/api/v1/gatherings?kind=share")) == ["모래 나눔"]
    assert titles(host.get("/api/v1/gatherings?species=cat")) == ["모래 나눔"]


@pytest.mark.django_db
def test_blocked_hosts_gatherings_hidden(member_api):
    host = member_api()
    viewer = member_api()
    host.post("/api/v1/gatherings", walk(), format="json")
    viewer.post(f"/api/v1/users/{host.user.id}/block")
    assert viewer.get("/api/v1/gatherings").data["results"] == []
