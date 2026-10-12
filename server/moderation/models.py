from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Report(models.Model):
    """신고. 글·댓글 등 어떤 콘텐츠에도 붙일 수 있다."""

    class Reason(models.TextChoices):
        MONEY = "money", "금전 요구"
        SPAM = "spam", "광고·도배"
        ABUSE = "abuse", "욕설·비하"
        DANGER = "danger", "동물 학대·위험"
        OTHER = "other", "기타"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    reason = models.CharField(max_length=10, choices=Reason.choices)
    detail = models.CharField(max_length=300, blank=True)
    resolved = models.BooleanField(default=False, help_text="운영자 검토 완료")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "content_type", "object_id"], name="uniq_report_per_user"
            )
        ]
        indexes = [models.Index(fields=["content_type", "object_id"])]
