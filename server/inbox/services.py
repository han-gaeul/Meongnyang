"""쪽지 보낼 수 있는 상대.

모르는 사람에게 쪽지가 쏟아지지 않도록, 앱 안에서 이미 연결된 사이만 허용한다.
- 만남 인증을 한 이웃
- 같은 모임의 모임장·신청자(취소 제외)
- 같은 부탁의 부탁한 사람·신청한 이웃
- 상대가 먼저 쪽지를 보낸 경우(답장)
차단 관계, 탈퇴·미인증 상대는 안 된다.
"""

from dataclasses import dataclass

from django.db.models import Q

from .models import Message


@dataclass(frozen=True)
class CanSend:
    ok: bool
    reason: str = ""


def _connected(a, b) -> bool:
    from favors.models import FavorApplication
    from gatherings.models import Participation
    from meetups.services import meet_count

    if meet_count(a.id, b.id) > 0:
        return True
    if Message.objects.filter(sender=b, recipient=a).exists():
        return True
    live = ~Q(status="cancelled")
    if Participation.objects.filter(
        live, Q(gathering__host=a, user=b) | Q(gathering__host=b, user=a)
    ).exists():
        return True
    # 같은 모임에 함께 수락된 참여자끼리
    mine = Participation.objects.filter(user=a, status="accepted").values("gathering")
    if Participation.objects.filter(user=b, status="accepted", gathering__in=mine).exists():
        return True
    if FavorApplication.objects.filter(live, Q(favor__requester=a, user=b) | Q(favor__requester=b, user=a)).exists():
        return True
    return False


def can_send(sender, recipient) -> CanSend:
    if recipient is None or not recipient.is_active:
        return CanSend(False, "상대를 찾을 수 없어요.")
    if sender.id == recipient.id:
        return CanSend(False, "나에게는 보낼 수 없어요.")
    if sender.blocks.filter(pk=recipient.pk).exists() or recipient.blocks.filter(pk=sender.pk).exists():
        return CanSend(False, "쪽지를 보낼 수 없는 상대예요.")
    if not recipient.is_verified_member:
        return CanSend(False, "상대가 아직 인증 회원이 아니에요.")
    if not _connected(sender, recipient):
        return CanSend(False, "만남 인증을 했거나 같은 모임·부탁으로 연결된 이웃에게만 쪽지를 보낼 수 있어요.")
    return CanSend(True)


def threads(user, limit: int = 50) -> list[dict]:
    """상대별 마지막 쪽지와 안 읽은 수 (최근 대화 순)"""
    qs = Message.objects.filter(
        Q(sender=user, sender_deleted=False) | Q(recipient=user, recipient_deleted=False)
    ).select_related("sender", "recipient")[:1000]
    out: dict[int, dict] = {}
    for m in qs:
        other = m.recipient if m.sender_id == user.id else m.sender
        t = out.get(other.id)
        if t is None:
            if len(out) >= limit:
                continue
            t = out[other.id] = {"user": other, "last": m, "unread": 0}
        if m.recipient_id == user.id and m.read_at is None:
            t["unread"] += 1
    return list(out.values())
