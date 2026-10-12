from dataclasses import dataclass

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction

from .models import Report


@dataclass(frozen=True)
class ReportResult:
    created: bool  # False면 이미 신고한 콘텐츠
    hidden: bool  # 이번 신고로(또는 이미) 숨김 상태인가


def report_content(target, reporter, reason: str, detail: str = "") -> ReportResult:
    """신고를 남기고, 서로 다른 사람의 신고가 기준 이상 쌓이면 자동으로 숨긴다.

    같은 사람이 같은 콘텐츠를 여러 번 신고해도 1건으로 센다.
    숨긴 뒤 복구·제재는 운영자가 /admin에서 판단한다.
    """
    ct = ContentType.objects.get_for_model(target)
    try:
        with transaction.atomic():
            Report.objects.create(
                reporter=reporter, content_type=ct, object_id=target.pk, reason=reason, detail=detail
            )
        created = True
    except IntegrityError:
        created = False

    count = Report.objects.filter(content_type=ct, object_id=target.pk).count()
    if count >= settings.REPORT_HIDE_THRESHOLD and not target.is_hidden:
        target.is_hidden = True
        target.save(update_fields=["is_hidden"])
    return ReportResult(created=created, hidden=target.is_hidden)
