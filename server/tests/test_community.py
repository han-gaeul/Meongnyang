from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from community.models import Comment, Post

POST = {"title": "대형견 산책 코스 추천해요", "content": "한강 쪽이 넓어서 좋아요", "species": "dog", "tags": ["#산책", "대형견"]}


def png_file(name="a.png", size=(40, 30)):
    buf = BytesIO()
    Image.new("RGB", size, (200, 120, 50)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


# ---- 인증 전 둘러보기 / 쓰기 권한 ----


@pytest.mark.django_db
def test_unverified_user_can_read_but_not_write(auth_api, member_api):
    writer = member_api()
    writer.post("/api/v1/posts", POST, format="json")
    viewer = auth_api()  # 가입만 하고 인증 전

    res = viewer.get("/api/v1/posts")
    assert res.status_code == 200
    assert len(res.data["results"]) == 1

    assert viewer.post("/api/v1/posts", POST, format="json").status_code == 403
    post_id = res.data["results"][0]["id"]
    assert viewer.post(f"/api/v1/posts/{post_id}/like").status_code == 403
    assert viewer.post(f"/api/v1/posts/{post_id}/comments", {"content": "hi"}, format="json").status_code == 403
    assert viewer.get(f"/api/v1/posts/{post_id}/comments").status_code == 200


@pytest.mark.django_db
def test_anonymous_cannot_read(api):
    assert api.get("/api/v1/posts").status_code == 401


@pytest.mark.django_db
def test_create_post_with_tags(member_api):
    client = member_api()
    client.user.region_name = "망원동"
    client.user.save()
    res = client.post("/api/v1/posts", POST, format="json")
    assert res.status_code == 201
    assert res.data["tags"] == ["산책", "대형견"]
    assert res.data["region_name"] == "망원동"
    assert res.data["author"]["nickname"] == client.user.nickname
    assert res.data["is_mine"] is True
    assert res.data["like_count"] == 0


# ---- 작성자만 수정·삭제 ----


@pytest.mark.django_db
def test_only_author_can_edit_or_delete(member_api):
    author = member_api()
    other = member_api()
    post_id = author.post("/api/v1/posts", POST, format="json").data["id"]

    assert other.patch(f"/api/v1/posts/{post_id}", {"title": "x"}, format="json").status_code == 403
    assert other.delete(f"/api/v1/posts/{post_id}").status_code == 403
    res = author.patch(f"/api/v1/posts/{post_id}", {"title": "수정됨", "tags": ["고양이"]}, format="json")
    assert res.status_code == 200
    assert res.data["title"] == "수정됨"
    assert res.data["tags"] == ["고양이"]
    assert author.delete(f"/api/v1/posts/{post_id}").status_code == 204


@pytest.mark.django_db
def test_only_author_can_delete_comment(member_api):
    author = member_api()
    other = member_api()
    post_id = author.post("/api/v1/posts", POST, format="json").data["id"]
    comment_id = other.post(f"/api/v1/posts/{post_id}/comments", {"content": "좋아요"}, format="json").data["id"]
    assert author.delete(f"/api/v1/comments/{comment_id}").status_code == 403
    assert other.delete(f"/api/v1/comments/{comment_id}").status_code == 204


# ---- 좋아요 / 댓글 수 ----


@pytest.mark.django_db
def test_like_unlike_counts(member_api):
    author = member_api()
    fan = member_api()
    post_id = author.post("/api/v1/posts", POST, format="json").data["id"]

    res = fan.post(f"/api/v1/posts/{post_id}/like")
    assert res.data["like_count"] == 1 and res.data["is_liked"] is True
    res = fan.post(f"/api/v1/posts/{post_id}/like")  # 중복 좋아요는 1개
    assert res.data["like_count"] == 1
    res = fan.delete(f"/api/v1/posts/{post_id}/like")
    assert res.data["like_count"] == 0 and res.data["is_liked"] is False

    fan.post(f"/api/v1/posts/{post_id}/comments", {"content": "1"}, format="json")
    fan.post(f"/api/v1/posts/{post_id}/comments", {"content": "2"}, format="json")
    assert author.get(f"/api/v1/posts/{post_id}").data["comment_count"] == 2


# ---- 필터 / 검색 ----


@pytest.mark.django_db
def test_filters(member_api):
    client = member_api()
    client.post("/api/v1/posts", {**POST, "species": "dog"}, format="json")
    client.post("/api/v1/posts", {"title": "고양이 모래 추천", "content": "두부 모래", "species": "cat", "tags": ["모래"]}, format="json")
    client.post("/api/v1/posts", {"title": "동네 동물병원", "content": "24시", "species": "all"}, format="json")

    titles = lambda res: {p["title"] for p in res.data["results"]}  # noqa: E731
    assert titles(client.get("/api/v1/posts?species=cat")) == {"고양이 모래 추천", "동네 동물병원"}
    assert titles(client.get("/api/v1/posts?tag=%23모래")) == {"고양이 모래 추천"}
    assert titles(client.get("/api/v1/posts?q=24시")) == {"동네 동물병원"}


# ---- 신고 자동 숨김 ----


@pytest.mark.django_db
def test_three_reports_hide_post(settings, member_api):
    settings.REPORT_HIDE_THRESHOLD = 3
    author = member_api()
    reporters = [member_api() for _ in range(3)]
    viewer = member_api()
    post_id = author.post("/api/v1/posts", POST, format="json").data["id"]

    r1 = reporters[0].post(f"/api/v1/posts/{post_id}/report", {"reason": "money"}, format="json")
    assert r1.data == {"created": True, "hidden": False}
    # 같은 사람이 여러 번 신고해도 1건
    r1b = reporters[0].post(f"/api/v1/posts/{post_id}/report", {"reason": "money"}, format="json")
    assert r1b.data == {"created": False, "hidden": False}
    reporters[1].post(f"/api/v1/posts/{post_id}/report", {"reason": "money"}, format="json")
    r3 = reporters[2].post(f"/api/v1/posts/{post_id}/report", {"reason": "spam"}, format="json")
    assert r3.data["hidden"] is True

    assert Post.objects.get(pk=post_id).is_hidden
    assert viewer.get("/api/v1/posts").data["results"] == []
    assert viewer.get(f"/api/v1/posts/{post_id}").status_code == 404
    # 작성자에게는 숨김 표시와 함께 보인다
    mine = author.get(f"/api/v1/posts/{post_id}")
    assert mine.status_code == 200 and mine.data["is_hidden"] is True


@pytest.mark.django_db
def test_cannot_report_own_post(member_api):
    author = member_api()
    post_id = author.post("/api/v1/posts", POST, format="json").data["id"]
    assert author.post(f"/api/v1/posts/{post_id}/report", {"reason": "spam"}, format="json").status_code == 400


@pytest.mark.django_db
def test_hidden_comment_not_counted_or_listed(settings, member_api):
    settings.REPORT_HIDE_THRESHOLD = 1
    author = member_api()
    commenter = member_api()
    reporter = member_api()
    post_id = author.post("/api/v1/posts", POST, format="json").data["id"]
    cid = commenter.post(f"/api/v1/posts/{post_id}/comments", {"content": "돈 보내주세요"}, format="json").data["id"]

    reporter.post(f"/api/v1/comments/{cid}/report", {"reason": "money"}, format="json")
    assert Comment.objects.get(pk=cid).is_hidden
    assert author.get(f"/api/v1/posts/{post_id}/comments").data == []
    assert author.get(f"/api/v1/posts/{post_id}").data["comment_count"] == 0


# ---- 차단 ----


@pytest.mark.django_db
def test_blocked_users_content_hidden_both_ways(member_api):
    a = member_api()
    b = member_api()
    b.post("/api/v1/posts", POST, format="json")
    a.post("/api/v1/posts", {**POST, "title": "a의 글"}, format="json")

    a.post(f"/api/v1/users/{b.user.id}/block")
    assert {p["title"] for p in a.get("/api/v1/posts").data["results"]} == {"a의 글"}
    # 차단당한 쪽에서도 차단한 사람의 글이 보이지 않는다
    assert {p["title"] for p in b.get("/api/v1/posts").data["results"]} == {POST["title"]}


# ---- 사진 업로드 ----


@pytest.mark.django_db
def test_upload_and_attach_images(member_api):
    client = member_api()
    res = client.post("/api/v1/uploads/images", {"file": png_file()}, format="multipart")
    assert res.status_code == 201
    assert res.data["url"].endswith(".jpg")
    image_id = res.data["id"]

    res = client.post("/api/v1/posts", {**POST, "image_ids": [image_id]}, format="json")
    assert res.status_code == 201
    assert [img["id"] for img in res.data["images"]] == [image_id]

    # 같은 사진을 다른 글에 다시 쓸 수 없다
    res = client.post("/api/v1/posts", {**POST, "image_ids": [image_id]}, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_cannot_attach_others_image(member_api):
    owner = member_api()
    thief = member_api()
    image_id = owner.post("/api/v1/uploads/images", {"file": png_file()}, format="multipart").data["id"]
    res = thief.post("/api/v1/posts", {**POST, "image_ids": [image_id]}, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_upload_rejects_non_image(member_api):
    client = member_api()
    fake = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")
    assert client.post("/api/v1/uploads/images", {"file": fake}, format="multipart").status_code == 400


@pytest.mark.django_db
def test_unverified_cannot_upload(auth_api):
    client = auth_api()
    assert client.post("/api/v1/uploads/images", {"file": png_file()}, format="multipart").status_code == 403


@pytest.mark.django_db
def test_upload_strips_exif_location(member_api, tmp_path):
    client = member_api()
    img = Image.new("RGB", (20, 20))
    exif = img.getexif()
    exif[0x8825] = {1: "N", 3: "E"}  # GPSInfo (위도·경도 방향만 넣은 최소 예시)
    buf = BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    res = client.post(
        "/api/v1/uploads/images",
        {"file": SimpleUploadedFile("gps.jpg", buf.getvalue(), content_type="image/jpeg")},
        format="multipart",
    )
    assert res.status_code == 201
    from uploads.models import UploadedImage

    stored = UploadedImage.objects.get(pk=res.data["id"])
    with Image.open(stored.file.path) as saved:
        assert 0x8825 not in saved.getexif()
