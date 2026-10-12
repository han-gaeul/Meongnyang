from django.db.models import Q, QuerySet


def visible_to(qs: QuerySet, user, author_field: str = "user") -> QuerySet:
    """숨김 처리된 콘텐츠와 차단 관계인 사용자의 콘텐츠를 뺀다.

    - 숨김 콘텐츠는 작성자 본인에게만 보인다(숨겨졌다는 사실을 알 수 있게).
    - 내가 차단한 사람, 나를 차단한 사람의 콘텐츠는 서로 보이지 않는다.
    """
    qs = qs.filter(Q(is_hidden=False) | Q(**{author_field: user}))
    blocked_ids = set(user.blocks.values_list("id", flat=True)) | set(
        user.blocked_by.values_list("id", flat=True)
    )
    if blocked_ids:
        qs = qs.exclude(**{f"{author_field}__in": blocked_ids})
    return qs
