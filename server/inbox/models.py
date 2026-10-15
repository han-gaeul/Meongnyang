from django.conf import settings
from django.db import models

from common.models import Moderated


class Message(Moderated):
    """1:1 쪽지. 보낸 사람·받은 사람이 각자 지울 수 있다(상대 쪽에는 남음).

    is_hidden(신고 누적)은 운영자 검토 표시용이다. 받은 사람은 신고하는 즉시 자기 쪽지함에서 숨긴다.
    """

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField(max_length=1000)
    read_at = models.DateTimeField(null=True, blank=True)
    sender_deleted = models.BooleanField(default=False)
    recipient_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["recipient", "read_at"]), models.Index(fields=["sender", "recipient"])]
