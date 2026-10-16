from django.db import transaction

from . import push
from .models import DeviceToken, Notification


def notify(user, kind: str, title: str, body: str = "", path: str = "") -> Notification:
    """알림을 남기고, 커밋된 뒤 푸시를 보낸다(요청이 실패하면 푸시도 안 감)."""
    data = {"path": path} if path else {}
    n = Notification.objects.create(user=user, kind=kind, title=title[:100], body=body[:200], data=data)

    def _send():
        tokens = list(DeviceToken.objects.filter(user=user, active=True).values_list("token", flat=True))
        dead = push.send(tokens, n.title, n.body, {**data, "notification_id": n.id})
        if dead:
            DeviceToken.objects.filter(token__in=dead).update(active=False)

    transaction.on_commit(_send)
    return n
