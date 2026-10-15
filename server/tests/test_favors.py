from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from favors.models import Favor
from meetups.models import Meetup
from pets.models import Pet


def meet(a, b, times=1, days_ago=0):
    lo, hi = sorted([a.id, b.id])
    today = timezone.localdate()
    for i in range(days_ago, days_ago + times):
        Meetup.objects.create(user_a_id=lo, user_b_id=hi, met_on=today - timedelta(days=i), distance_m=5)


def pet_of(client):
    return Pet.objects.filter(user=client.user, verification_status="approved").first()


def favor(client, **overrides):
    data = {
        "pet_id": pet_of(client).id,
        "kind": "walk",
        "title": "저녁 산책 30분만 부탁해요",
        "content": "야근이라 늦어요",
        "place_name": "망원동 OO아파트 정문",
        "starts_at": (timezone.now() + timedelta(days=1)).isoformat(),
        "duration_minutes": 30,
        "agree_terms": True,
        "care_sheet_input": {
            "meal": {"times_per_day": 2, "amount": "1컵", "food": "로얄캐닌"},
            "meds": [{"name": "심장사상충약", "dose": "1알", "time": "저녁"}],
            "walk": {"minutes": 40, "per_week": 7},
            "caution": "자전거를 보면 짖어요",
        },
    }
    data.update(overrides)
    return client.post("/api/v1/favors", data, format="json")


@pytest.fixture
def pair(member_api):
    """서로 한 번 만난 보호자(owner)와 이웃(neighbor), 만난 적 없는 사람(stranger)"""
    owner, neighbor, stranger = member_api(), member_api(), member_api()
    meet(owner.user, neighbor.user)
    return owner, neighbor, stranger


@pytest.mark.django_db
def test_care_sheet_draft_uses_pet_profile_and_is_owner_only(member_api):
    owner, other = member_api(), member_api()
    pet = pet_of(owner)
    pet.traits = ["순해요", "사람 좋아해요"]
    pet.size = "L"
    pet.save()

    res = owner.get(f"/api/v1/pets/{pet.id}/care-sheet?days=30")
    assert res.status_code == 200
    assert res.data["basic"]["name"] == "콩이"
    assert res.data["basic"]["traits"] == ["순해요", "사람 좋아해요"]
    assert res.data["source"]["days"] == 30
    assert res.data["meds"] == []
    assert other.get(f"/api/v1/pets/{pet.id}/care-sheet").status_code == 404


@pytest.mark.django_db
def test_create_requires_agreement_short_duration_and_own_verified_pet(pair, member_api):
    owner, neighbor, _ = pair
    assert favor(owner, agree_terms=False).status_code == 400
    assert favor(owner, duration_minutes=180).status_code == 400  # 긴 부탁은 1.1
    assert favor(owner, pet_id=pet_of(neighbor).id).status_code == 400
    assert favor(owner, place_name="").status_code == 400
    unverified = Pet.objects.create(user=owner.user, name="나비", species="cat")
    assert favor(owner, pet_id=unverified.id).status_code == 400

    res = favor(owner)
    assert res.status_code == 201, res.data
    sheet = res.data["care_sheet"]
    assert sheet["basic"]["name"] == "콩이"  # 서버가 프로필로 채움
    assert sheet["meds"][0]["name"] == "심장사상충약"
    assert "source" not in sheet


@pytest.mark.django_db
def test_only_neighbors_see_favor_and_details_stay_private(pair):
    owner, neighbor, stranger = pair
    fid = favor(owner).data["id"]

    assert [f["id"] for f in neighbor.get("/api/v1/favors").data["results"]] == [fid]
    assert stranger.get("/api/v1/favors").data["results"] == []
    assert stranger.get(f"/api/v1/favors/{fid}").status_code == 404

    seen = neighbor.get(f"/api/v1/favors/{fid}").data
    assert seen["care_sheet"] is None  # 약·식사는 맡은 이웃에게만
    assert seen["care_summary"]["walk"]["minutes"] == 40
    assert seen["can_help"] is True
    assert owner.get("/api/v1/favors").data["results"] == []  # 내 부탁은 이웃 목록에 안 나옴
    assert [f["id"] for f in owner.get("/api/v1/favors?mine=1").data["results"]] == [fid]


@pytest.mark.django_db
def test_full_flow_apply_accept_complete_thank(pair, member_api):
    owner, neighbor, _ = pair
    other = member_api()
    meet(owner.user, other.user)
    fid = favor(owner).data["id"]

    assert neighbor.post(f"/api/v1/favors/{fid}/apply", {"message": "제가 갈게요"}, format="json").status_code == 400
    assert neighbor.post(f"/api/v1/favors/{fid}/apply", {"agree_terms": True}, format="json").status_code == 200
    assert neighbor.post(f"/api/v1/favors/{fid}/apply", {"agree_terms": True}, format="json").status_code == 409
    assert other.post(f"/api/v1/favors/{fid}/apply", {"agree_terms": True}, format="json").status_code == 200
    assert owner.get(f"/api/v1/favors/{fid}").data["pending_count"] == 2

    assert neighbor.get(f"/api/v1/favors/{fid}/applications").status_code == 403
    apps = {a["user"]["id"]: a["id"] for a in owner.get(f"/api/v1/favors/{fid}/applications").data}

    res = owner.post(f"/api/v1/favors/{fid}/applications/{apps[neighbor.user.id]}/accept")
    assert res.status_code == 200
    assert res.data["status"] == "matched"
    assert res.data["helper"]["id"] == neighbor.user.id
    # 이미 약속했으면 다른 신청은 수락 불가
    assert owner.post(f"/api/v1/favors/{fid}/applications/{apps[other.user.id]}/accept").status_code == 400

    # 맡은 이웃만 전체 시트를 본다
    assert neighbor.get(f"/api/v1/favors/{fid}").data["care_sheet"]["caution"] == "자전거를 보면 짖어요"
    assert other.get(f"/api/v1/favors/{fid}").data["care_sheet"] is None

    # 시간 전에는 이웃도 '다 했어요'를 못 누르고, 보호자도 확인 불가
    assert neighbor.post(f"/api/v1/favors/{fid}/finish").status_code == 400
    assert owner.post(f"/api/v1/favors/{fid}/complete").status_code == 400
    Favor.objects.filter(pk=fid).update(starts_at=timezone.now() - timedelta(minutes=5))
    # 시간이 됐어도 이웃이 알리기 전(약속 30분 안)엔 보호자 확인 불가
    assert owner.get(f"/api/v1/favors/{fid}").data["can_confirm"] is False
    assert owner.post(f"/api/v1/favors/{fid}/complete").status_code == 400
    # 보호자는 '다 했어요'를 누를 수 없고, 맡은 이웃은 완료 확인을 할 수 없다
    assert owner.post(f"/api/v1/favors/{fid}/finish").status_code == 400
    assert neighbor.post(f"/api/v1/favors/{fid}/complete").status_code == 403
    assert other.post(f"/api/v1/favors/{fid}/finish").status_code == 400

    res = neighbor.post(f"/api/v1/favors/{fid}/finish")
    assert res.status_code == 200 and res.data["helper_reported_at"]
    assert res.data["can_confirm"] is False  # 이웃에겐 확인 버튼 없음
    assert owner.get(f"/api/v1/favors/{fid}").data["can_confirm"] is True
    assert owner.post(f"/api/v1/favors/{fid}/thank", {"message": "고마워요"}, format="json").status_code == 400
    assert owner.post(f"/api/v1/favors/{fid}/complete").data["status"] == "done"

    res = owner.post(f"/api/v1/favors/{fid}/thank", {"message": "콩이가 신났어요, 고마워요!"}, format="json")
    assert res.data["thanks"]["message"].startswith("콩이가")
    assert owner.post(f"/api/v1/favors/{fid}/thank", {"message": "또"}, format="json").status_code == 409

    # 완료된 부탁은 지워지지 않는다
    owner.delete(f"/api/v1/favors/{fid}")
    assert Favor.objects.filter(pk=fid).exists()


@pytest.mark.django_db
def test_stranger_cannot_apply(pair):
    owner, _, stranger = pair
    fid = favor(owner).data["id"]
    # 목록·상세에서 안 보이므로 신청도 404
    assert stranger.post(f"/api/v1/favors/{fid}/apply", {"agree_terms": True}, format="json").status_code == 404


@pytest.mark.django_db
def test_helper_withdraw_reopens_favor(pair):
    owner, neighbor, _ = pair
    fid = favor(owner).data["id"]
    neighbor.post(f"/api/v1/favors/{fid}/apply", {"agree_terms": True}, format="json")
    aid = owner.get(f"/api/v1/favors/{fid}/applications").data[0]["id"]
    owner.post(f"/api/v1/favors/{fid}/applications/{aid}/accept")

    res = neighbor.post(f"/api/v1/favors/{fid}/withdraw")
    assert res.data["status"] == "open"
    assert res.data["helper"] is None
    assert res.data["care_sheet"] is None


@pytest.mark.django_db
def test_matched_favor_cannot_be_edited(pair):
    owner, neighbor, _ = pair
    fid = favor(owner).data["id"]
    assert owner.patch(f"/api/v1/favors/{fid}", {"title": "고쳤어요"}, format="json").status_code == 200
    neighbor.post(f"/api/v1/favors/{fid}/apply", {"agree_terms": True}, format="json")
    aid = owner.get(f"/api/v1/favors/{fid}/applications").data[0]["id"]
    owner.post(f"/api/v1/favors/{fid}/applications/{aid}/accept")
    assert owner.patch(f"/api/v1/favors/{fid}", {"title": "또 고침"}, format="json").status_code == 400
    assert neighbor.patch(f"/api/v1/favors/{fid}", {"title": "남의 글"}, format="json").status_code == 403


@pytest.mark.django_db
def test_visit_home_needs_regular_neighbor(pair):
    owner, neighbor, _ = pair
    meet(owner.user, neighbor.user, times=2, days_ago=1)  # 어제·그제 → 총 3번 만남

    visit = favor(owner, kind="meal", visit_home=True, place_name="").data["id"]
    data = neighbor.get(f"/api/v1/favors/{visit}").data
    assert data["can_help"] is False
    assert "단골 이웃" in data["cannot_help_reason"]
    assert neighbor.post(f"/api/v1/favors/{visit}/apply", {"agree_terms": True}, format="json").status_code == 403
    assert neighbor.get("/api/v1/neighbors").data[0]["level"] == "neighbor"

    # 짧은 부탁을 한 번 함께 마치면 단골 이웃
    Favor.objects.create(
        requester=owner.user, pet=pet_of(owner), kind="walk", title="t", starts_at=timezone.now(),
        duration_minutes=30, requester_agreed_at=timezone.now(), status=Favor.Status.DONE, helper=neighbor.user,
    )
    assert neighbor.get("/api/v1/neighbors").data[0]["level"] == "regular"
    assert neighbor.get(f"/api/v1/favors/{visit}").data["can_help"] is True
    assert neighbor.post(f"/api/v1/favors/{visit}/apply", {"agree_terms": True}, format="json").status_code == 200


@pytest.mark.django_db
def test_blocked_neighbor_cannot_see_or_apply(pair):
    owner, neighbor, _ = pair
    fid = favor(owner).data["id"]
    owner.user.blocks.add(neighbor.user)
    assert neighbor.get("/api/v1/favors").data["results"] == []
    assert neighbor.post(f"/api/v1/favors/{fid}/apply", {"agree_terms": True}, format="json").status_code == 404


@pytest.mark.django_db
def test_unverified_cannot_create(auth_api):
    guest = auth_api()
    with mock.patch("favors.views.FavorViewSet.create") as create:
        assert guest.post("/api/v1/favors", {}, format="json").status_code == 403
        create.assert_not_called()


@pytest.mark.django_db
def test_requester_can_confirm_after_end_even_without_report(pair):
    """이웃이 '다 했어요'를 깜빡해도 약속 시간이 끝나면 보호자가 완료할 수 있다"""
    owner, neighbor, _ = pair
    fid = favor(owner).data["id"]
    neighbor.post(f"/api/v1/favors/{fid}/apply", {"agree_terms": True}, format="json")
    aid = owner.get(f"/api/v1/favors/{fid}/applications").data[0]["id"]
    owner.post(f"/api/v1/favors/{fid}/applications/{aid}/accept")
    Favor.objects.filter(pk=fid).update(starts_at=timezone.now() - timedelta(minutes=31))
    assert owner.post(f"/api/v1/favors/{fid}/complete").data["status"] == "done"
