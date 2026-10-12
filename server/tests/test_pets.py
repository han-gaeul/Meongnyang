import pytest

from pets.models import Pet

PET = {"name": "콩이", "species": "dog", "size": "L", "weight_kg": "28.5", "traits": ["순함", "사람 좋아함"]}


@pytest.fixture
def verified_client(auth_api):
    def _make(person):
        client = auth_api()
        res = client.post("/api/v1/auth/identity/verify", {"transaction_id": f"mock-ok-{person}"}, format="json")
        assert res.status_code == 200
        return client

    return _make


@pytest.mark.django_db
def test_create_and_list_my_pets(auth_api):
    client = auth_api()
    res = client.post("/api/v1/pets", PET, format="json")
    assert res.status_code == 201
    assert res.data["user"] == client.user.id
    assert res.data["verification_status"] == "unverified"
    assert len(client.get("/api/v1/pets").data["results"]) == 1


@pytest.mark.django_db
def test_cannot_set_verification_status_directly(auth_api):
    client = auth_api()
    res = client.post("/api/v1/pets", {**PET, "verification_status": "approved"}, format="json")
    assert res.data["verification_status"] == "unverified"


@pytest.mark.django_db
def test_other_user_cannot_update_or_delete(auth_api):
    owner = auth_api()
    pet_id = owner.post("/api/v1/pets", PET, format="json").data["id"]
    other = auth_api()

    assert other.get(f"/api/v1/pets/{pet_id}").status_code == 200  # 읽기는 가능
    assert other.patch(f"/api/v1/pets/{pet_id}", {"name": "해킹"}, format="json").status_code == 403
    assert other.delete(f"/api/v1/pets/{pet_id}").status_code == 403
    assert Pet.objects.get(pk=pet_id).name == "콩이"


@pytest.mark.django_db
def test_owner_can_delete(auth_api):
    owner = auth_api()
    pet_id = owner.post("/api/v1/pets", PET, format="json").data["id"]
    assert owner.delete(f"/api/v1/pets/{pet_id}").status_code == 204


@pytest.mark.django_db
def test_anonymous_cannot_access(api):
    assert api.get("/api/v1/pets").status_code == 401


@pytest.mark.django_db
def test_verify_requires_identity(auth_api):
    client = auth_api()
    pet_id = client.post("/api/v1/pets", PET, format="json").data["id"]
    res = client.post(f"/api/v1/pets/{pet_id}/verify", {"registration_number": "410000000000001"}, format="json")
    assert res.status_code == 403


@pytest.mark.django_db
def test_verify_registry_match_approves(verified_client):
    client = verified_client("p1")
    pet_id = client.post("/api/v1/pets", PET, format="json").data["id"]
    res = client.post(f"/api/v1/pets/{pet_id}/verify", {"registration_number": "410000000000001"}, format="json")
    assert res.status_code == 200
    assert res.data["verification_status"] == "approved"
    assert "registration_number" not in res.data
    client.user.refresh_from_db()
    assert client.user.is_verified_member is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("reg_no", "expected"),
    [("010000000000001", "pending"), ("910000000000001", "rejected")],
)
def test_verify_not_found_or_mismatch(verified_client, reg_no, expected):
    client = verified_client("p2")
    pet_id = client.post("/api/v1/pets", PET, format="json").data["id"]
    res = client.post(f"/api/v1/pets/{pet_id}/verify", {"registration_number": reg_no}, format="json")
    assert res.data["verification_status"] == expected
    client.user.refresh_from_db()
    assert client.user.is_verified_member is False


@pytest.mark.django_db
def test_verify_rejects_bad_format(verified_client):
    client = verified_client("p3")
    pet_id = client.post("/api/v1/pets", PET, format="json").data["id"]
    res = client.post(f"/api/v1/pets/{pet_id}/verify", {"registration_number": "12345"}, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_same_registration_number_cannot_be_used_twice(verified_client):
    a = verified_client("a")
    b = verified_client("b")
    pa = a.post("/api/v1/pets", PET, format="json").data["id"]
    pb = b.post("/api/v1/pets", PET, format="json").data["id"]
    reg = {"registration_number": "410000000000009"}
    assert a.post(f"/api/v1/pets/{pa}/verify", reg, format="json").status_code == 200
    assert b.post(f"/api/v1/pets/{pb}/verify", reg, format="json").status_code == 409


@pytest.mark.django_db
def test_other_user_cannot_verify_my_pet(verified_client):
    owner = verified_client("o")
    other = verified_client("x")
    pet_id = owner.post("/api/v1/pets", PET, format="json").data["id"]
    res = other.post(f"/api/v1/pets/{pet_id}/verify", {"registration_number": "410000000000001"}, format="json")
    assert res.status_code == 403
