from datetime import timedelta

import pytest
from django.utils import timezone

from pets.models import Pet
from places.models import Place, PlaceReview

HERE = {"lat": 37.5556, "lng": 126.9019}


def at(north=0, east=0):
    import math

    return {
        "lat": HERE["lat"] + north / 111_320,
        "lng": HERE["lng"] + east / (111_320 * math.cos(math.radians(HERE["lat"]))),
    }


def place(name="멍카페", category="cafe", north=0, east=0, **kw):
    kw.setdefault("status", Place.Status.APPROVED)
    return Place.objects.create(name=name, category=category, **at(north, east), **kw)


def big_dog(client, weight=28, size="L"):
    pet = Pet.objects.filter(user=client.user).first()
    pet.size, pet.weight_kg = size, weight
    pet.save()
    return pet


def search(client, **params):
    q = {**HERE, **params}
    return client.get("/api/v1/places", q)


@pytest.mark.django_db
def test_radius_search_sorted_by_distance_and_hides_pending(member_api, auth_api):
    viewer = auth_api()  # 인증 전에도 지도는 볼 수 있다
    place("가까운 곳", north=100)
    place("먼 곳", north=2000)
    place("반경 밖", north=5000)
    place("검토 대기", north=50, status=Place.Status.PENDING)
    place("폐업", north=60, status=Place.Status.CLOSED)

    res = search(viewer, radius=3000)
    assert res.status_code == 200
    assert [p["name"] for p in res.data] == ["가까운 곳", "먼 곳"]
    assert 90 <= res.data[0]["distance_m"] <= 110
    assert res.data[0]["kakao"]["directions"].startswith("https://map.kakao.com/link/to/")
    assert search(viewer).status_code == 200
    assert viewer.get("/api/v1/places", {"lat": "x", "lng": 1}).status_code == 400


@pytest.mark.django_db
def test_category_and_name_filters(auth_api):
    viewer = auth_api()
    place("A카페", "cafe")
    place("B병원", "hospital", is_24h=True)
    place("C식당", "restaurant")
    assert {p["name"] for p in search(viewer, category="cafe,restaurant").data} == {"A카페", "C식당"}
    assert [p["name"] for p in search(viewer, q="병원").data] == ["B병원"]
    assert [p["name"] for p in search(viewer, chips="24h").data] == ["B병원"]


@pytest.mark.django_db
def test_fit_for_my_large_dog(member_api):
    me = member_api()
    pet = big_dog(me, weight=28)
    small_only = place("소형견만", sizes_allowed=["S"], max_weight_kg=7, policy_checked_at=timezone.now())
    all_sizes = place("대형견 환영", sizes_allowed=["S", "M", "L"], policy_checked_at=timezone.now())
    weight_cap = place("20kg까지", sizes_allowed=["S", "M", "L"], max_weight_kg=20, policy_checked_at=timezone.now())
    unknown = place("정보 없음")

    fits = {p["name"]: p["fit"] for p in search(me, pet=pet.id).data}
    assert fits == {"소형견만": "no", "대형견 환영": "yes", "20kg까지": "no", "정보 없음": "unknown"}
    assert [p["name"] for p in search(me, pet=pet.id, fit="1").data] == ["대형견 환영"]

    # 비슷한 체중의 대형견이 실제로 함께 들어간 후기가 있으면 '갈 수 있음'
    other = member_api()
    other_pet = big_dog(other, weight=30)
    PlaceReview.objects.create(
        place=unknown, user=other.user, pet=other_pet, pet_species="dog", pet_size="L", pet_weight_kg=30,
        visited_on=timezone.localdate(), admitted=True,
    )
    assert {p["name"]: p["fit"] for p in search(me, pet=pet.id).data}["정보 없음"] == "yes"
    # 다른 사람 반려동물로는 계산하지 않는다
    assert search(me, pet=other_pet.id).data[0]["fit"] == "unknown"
    _ = (small_only, all_sizes, weight_cap)


@pytest.mark.django_db
def test_review_snapshot_visit_check_and_conditions(member_api):
    me = member_api()
    pet = big_dog(me, weight=32)
    cafe = place("테라스 카페", sizes_allowed=["S", "M"], space="indoor", policy_checked_at=timezone.now() - timedelta(days=30))

    body = {
        "pet_id": pet.id,
        "visited_on": timezone.localdate().isoformat(),
        "admitted": True,
        "space": "outdoor",
        "floor_ok": True,
        "extra_fee": False,
        "comment": "테라스에서만 가능했어요",
        **at(north=50),  # 장소 근처에서 작성
    }
    res = me.post(f"/api/v1/places/{cafe.id}/reviews", body, format="json")
    assert res.status_code == 201, res.data
    assert res.data["pet_size"] == "L" and res.data["pet_weight_kg"] == "32.0"
    assert res.data["verified_visit"] is True

    far = {**body, **at(north=2000)}
    assert me.post(f"/api/v1/places/{cafe.id}/reviews", far, format="json").data["verified_visit"] is False

    c = me.get(f"/api/v1/places/{cafe.id}").data["conditions"]
    assert c["review_count"] == 2
    assert c["large_reviews"] == 2
    assert c["max_weight_admitted"] == 32.0
    # 정책(소형·중형만, 실내)보다 최신 후기(대형견 입장, 테라스만)를 따른다
    assert c["large_ok"] is True
    assert c["space"] == "outdoor"
    assert c["differs_from_policy"] is True

    # 칩 필터: 대형견 OK·바닥 OK·추가요금 없음은 통과, 실내 OK는 탈락
    assert [p["id"] for p in search(me, chips="large,floor,nofee").data] == [cafe.id]
    assert search(me, chips="indoor").data == []


@pytest.mark.django_db
def test_review_rules(member_api, auth_api):
    me, other = member_api(), member_api()
    cafe = place()
    pet = Pet.objects.filter(user=me.user).first()
    other_pet = Pet.objects.filter(user=other.user).first()
    ok = {"pet_id": pet.id, "visited_on": timezone.localdate().isoformat(), "admitted": True}

    assert auth_api().post(f"/api/v1/places/{cafe.id}/reviews", ok, format="json").status_code == 403
    assert me.post(f"/api/v1/places/{cafe.id}/reviews", {**ok, "pet_id": other_pet.id}, format="json").status_code == 400
    future = (timezone.localdate() + timedelta(days=1)).isoformat()
    assert me.post(f"/api/v1/places/{cafe.id}/reviews", {**ok, "visited_on": future}, format="json").status_code == 400

    rid = me.post(f"/api/v1/places/{cafe.id}/reviews", ok, format="json").data["id"]
    listed = other.get(f"/api/v1/places/{cafe.id}/reviews").data["results"]
    assert [r["id"] for r in listed] == [rid]
    assert other.delete(f"/api/v1/place-reviews/{rid}").status_code == 403
    assert other.post(f"/api/v1/place-reviews/{rid}/report", {"reason": "spam"}, format="json").status_code == 200
    assert me.delete(f"/api/v1/place-reviews/{rid}").status_code == 204


@pytest.mark.django_db
def test_submit_place_goes_to_review_queue_and_blocks_duplicates(member_api, auth_api):
    me, other = member_api(), member_api()
    data = {
        "name": "새로 생긴 펫카페",
        "category": "cafe",
        **at(north=10),
        "sizes_allowed": ["L", "S", "L"],
        "space": "indoor",
        "floor_ok": True,
        "amenities": ["water"],
    }
    assert auth_api().post("/api/v1/places", data, format="json").status_code == 403
    res = me.post("/api/v1/places", data, format="json")
    assert res.status_code == 201, res.data
    pid = res.data["id"]
    assert res.data["status"] == "pending" and res.data["is_mine"] is True
    assert res.data["sizes_allowed"] == ["S", "L"]
    assert res.data["policy_checked_at"] is not None

    # 제보한 사람에게만 보이고, 후기는 승인 뒤에
    assert [p["id"] for p in search(me).data] == [pid]
    assert search(other).data == []
    rv = {"pet_id": Pet.objects.filter(user=me.user).first().id, "visited_on": timezone.localdate().isoformat(), "admitted": True}
    assert me.post(f"/api/v1/places/{pid}/reviews", rv, format="json").status_code == 400

    # 근처 같은 이름은 중복
    dup = other.post("/api/v1/places", {**data, "name": " 새로 생긴 펫카페 ", **at(north=60)}, format="json")
    assert dup.status_code == 409 and dup.data["id"] == pid
    assert other.post("/api/v1/places", {**data, **at(north=500)}, format="json").status_code == 201

    bad = me.post("/api/v1/places", {**data, "name": "해외", "lat": 48.8, "lng": 2.3}, format="json")
    assert bad.status_code == 400
    assert me.post("/api/v1/places", {**data, "name": "x", "amenities": ["pool"]}, format="json").status_code == 400


@pytest.mark.django_db
def test_seed_dev_places(settings):
    from django.core.management import call_command

    settings.DEBUG = True
    call_command("seed_dev_places", lat=HERE["lat"], lng=HERE["lng"])
    call_command("seed_dev_places", lat=HERE["lat"], lng=HERE["lng"])  # 다시 해도 중복 없음
    assert Place.objects.filter(source="dev").count() == 8
    assert all(p.name.startswith("[샘플]") for p in Place.objects.all())

    settings.DEBUG = False
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("seed_dev_places")
