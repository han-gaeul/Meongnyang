from django.db import models


class Moderated(models.Model):
    """신고 누적으로 숨겨질 수 있는 콘텐츠(글·댓글·모임글 등)의 공통 필드."""

    is_hidden = models.BooleanField(default=False, help_text="신고 누적 자동 숨김 또는 운영자 숨김")

    class Meta:
        abstract = True
