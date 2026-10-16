from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from gatherings.models import Gathering
from inbox.models import Message
from meetups.models import Meetup
from notifications.models import DeviceToken, Notification


def meet(a, b):
    lo, hi = sorted([a.id, b.id])
    Meetup.objects.create(user_a_id=lo, user_b_id=hi, met_on=timezone.localdate(), distance_m=3)


def send(client, to, text="안녕하세요"):
    return client.post("/api/v1/messages/send", {"recipient": to.id, "content": text}, format="json")


@pytest.mark.django_db
def test_only_connected_neighbors_can_message(member_api, auth_api):
    a, b, stranger = member_api(), member_api(), member_api()

    can = a.get("/api/v1/messages/can-send", {"to": b.user.id}).data
    assert can["ok"] is False and "만남 인증" in can["reason"]
    assert send(a, b.user).status_code == 403

    meet(a.user, b.user)
    assert a.get("/api/v1/messages/can-send", {"to": b.user.id}).data["ok"] is True
    assert send(a, b.user).status_code == 201
    assert send(a, a.user).status_code == 403
    assert send(stranger, a.user).status_code == 403
    # 미인증 회원은 보낼 수 없다
    assert send(auth_api(), a.user).status_code == 403

    # 차단하면 서로 못 보낸다
    b.user.blocks.add(a.user)
    assert send(a, b.user).status_code == 403
    assert send(b, a.user).status_code == 403


@pytest.mark.django_db
def test_gathering_host_and_applicant_can_message(member_api):
    host, guest = member_api(), member_api()
    g = Gathering.objects.create(
        host=host.user, kind="walk", title="산책", place_name="공원", starts_at=timezone.now() + timedelta(days=1)
    )
    assert send(guest, host.user).status_code == 403
    guest.post(f"/api/v1/gatherings/{g.id}/apply", {}, format="json")
    assert send(guest, host.user, "몇 시에 만나요?").status_code == 201
    # 받은 사람은 답장할 수 있다
    assert send(host, guest.user, "7시요").status_code == 201


@pytest.mark.django_db
def test_threads_read_delete_and_unread_counts(member_api):
    a, b, c = member_api(), member_api(), member_api()
    meet(a.user, b.user)
    meet(a.user, c.user)
    send(b, a.user, "첫 쪽지")
    send(b, a.user, "두 번째")
    send(c, a.user, "c예요")
    send(a, b.user, "답장")

    unread = a.get("/api/v1/notifications/unread").data
    assert unread == {"notifications": 3, "messages": 3}

    threads = a.get("/api/v1/messages/threads").data
    assert [t["user"]["id"] for t in threads] == [b.user.id, c.user.id]  # 최근 대화 순
    assert threads[0]["last"]["content"] == "답장" and threads[0]["last"]["is_mine"] is True
    assert threads[0]["unread"] == 2

    convo = a.get("/api/v1/messages", {"with": b.user.id}).data["results"]
    assert [m["content"] for m in convo] == ["답장", "두 번째", "첫 쪽지"]
    assert a.get("/api/v1/messages").status_code == 400

    assert a.post("/api/v1/messages/read", {"user": b.user.id}, format="json").status_code == 204
    assert a.get("/api/v1/notifications/unread").data == {"notifications": 1, "messages": 1}

    # 내 쪽에서만 지워진다
    mid = convo[2]["id"]
    assert a.delete(f"/api/v1/messages/{mid}").status_code == 204
    assert mid not in [m["id"] for m in a.get("/api/v1/messages", {"with": b.user.id}).data["results"]]
    assert mid in [m["id"] for m in b.get("/api/v1/messages", {"with": a.user.id}).data["results"]]
    # 남의 쪽지는 지울 수 없다
    other = Message.objects.filter(sender=c.user).first()
    assert b.delete(f"/api/v1/messages/{other.id}").status_code == 404


@pytest.mark.django_db
def test_report_message_hides_for_recipient(member_api):
    a, b = member_api(), member_api()
    meet(a.user, b.user)
    mid = send(a, b.user, "돈 보내 주세요").data["id"]
    assert a.post(f"/api/v1/messages/{mid}/report", {"reason": "money"}, format="json").status_code == 400
    res = b.post(f"/api/v1/messages/{mid}/report", {"reason": "money"}, format="json")
    assert res.status_code == 200
    assert b.get("/api/v1/messages", {"with": a.user.id}).data["results"] == []


@pytest.mark.django_db
def test_notifications_list_and_read(member_api):
    host, guest = member_api(), member_api()
    g = Gathering.objects.create(
        host=host.user, kind="walk", title="저녁 산책", place_name="공원", starts_at=timezone.now() + timedelta(days=1)
    )
    guest.post(f"/api/v1/gatherings/{g.id}/apply", {}, format="json")
    items = host.get("/api/v1/notifications").data["results"]
    assert items[0]["kind"] == "gathering_applied" and items[0]["path"] == f"/gatherings/{g.id}"

    pid = host.get(f"/api/v1/gatherings/{g.id}/applications").data[0]["id"]
    host.post(f"/api/v1/gatherings/{g.id}/applications/{pid}/accept")
    got = guest.get("/api/v1/notifications").data["results"][0]
    assert got["title"] == "모임 참여가 확정됐어요"

    assert host.post(f"/api/v1/notifications/{items[0]['id']}/read").status_code == 204
    assert host.get("/api/v1/notifications/unread").data["notifications"] == 0
    # 남의 알림은 못 본다
    assert items[0]["id"] not in [n["id"] for n in guest.get("/api/v1/notifications").data["results"]]
    assert guest.post("/api/v1/notifications/read-all").status_code == 204
    assert not Notification.objects.filter(user=guest.user, read_at__isnull=True).exists()


@pytest.mark.django_db
def test_favor_events_notify_both_sides(member_api):
    owner, helper = member_api(), member_api()
    meet(owner.user, helper.user)
    from pets.models import Pet

    pet = Pet.objects.filter(user=owner.user).first()
    fid = owner.post(
        "/api/v1/favors",
        {
            "pet_id": pet.id, "kind": "walk", "title": "산책 부탁", "place_name": "정문",
            "starts_at": (timezone.now() + timedelta(hours=1)).isoformat(), "duration_minutes": 30, "agree_terms": True,
        },
        format="json",
    ).data["id"]
    helper.post(f"/api/v1/favors/{fid}/apply", {"agree_terms": True}, format="json")
    aid = owner.get(f"/api/v1/favors/{fid}/applications").data[0]["id"]
    owner.post(f"/api/v1/favors/{fid}/applications/{aid}/accept")
    from favors.models import Favor

    Favor.objects.filter(pk=fid).update(starts_at=timezone.now() - timedelta(minutes=1))
    helper.post(f"/api/v1/favors/{fid}/finish")
    owner.post(f"/api/v1/favors/{fid}/complete")
    owner.post(f"/api/v1/favors/{fid}/thank", {"message": "고마워요!"}, format="json")

    kinds = lambda u: list(Notification.objects.filter(user=u).order_by("id").values_list("kind", flat=True))  # noqa: E731
    assert kinds(owner.user) == ["favor_applied", "favor_reported"]
    assert kinds(helper.user) == ["favor_matched", "favor_done", "favor_thanks"]


@pytest.mark.django_db
def test_device_token_register_and_push(member_api, settings, django_capture_on_commit_callbacks):
    a, b = member_api(), member_api()
    meet(a.user, b.user)
    token = "ExponentPushToken[abc123]"
    assert b.post("/api/v1/devices", {"token": "nope"}, format="json").status_code == 400
    assert b.post("/api/v1/devices", {"token": token, "platform": "ios"}, format="json").status_code == 204
    # 같은 기기에 다른 계정으로 로그인하면 토큰이 옮겨간다
    a.post("/api/v1/devices", {"token": token, "platform": "ios"}, format="json")
    assert DeviceToken.objects.get(token=token).user == a.user
    b.post("/api/v1/devices", {"token": token, "platform": "ios"}, format="json")

    settings.PUSH_ENABLED = True
    resp = mock.Mock()
    resp.json.return_value = {"data": [{"status": "error", "details": {"error": "DeviceNotRegistered"}}]}
    with mock.patch("notifications.push.requests.post", return_value=resp) as post:
        with django_capture_on_commit_callbacks(execute=True):
            send(a, b.user, "푸시 가나요")
    sent = post.call_args.kwargs["json"][0]
    assert sent["to"] == token and sent["title"].endswith("쪽지") and sent["data"]["path"] == f"/messages/{a.user.id}"
    # 기기에서 앱을 지운 토큰은 비활성화
    assert DeviceToken.objects.get(token=token).active is False

    assert b.delete("/api/v1/devices", {"token": token}, format="json").status_code == 204
    assert not DeviceToken.objects.filter(token=token).exists()


@pytest.mark.django_db
def test_push_disabled_sends_nothing(member_api, django_capture_on_commit_callbacks):
    a, b = member_api(), member_api()
    meet(a.user, b.user)
    DeviceToken.objects.create(user=b.user, token="ExponentPushToken[x]")
    with mock.patch("notifications.push.requests.post") as post:
        with django_capture_on_commit_callbacks(execute=True):
            send(a, b.user)
    post.assert_not_called()
