"""Expo 푸시 전송. https://docs.expo.dev/push-notifications/sending-notifications/

테스트·개발에서는 PUSH_ENABLED=False로 보내지 않는다.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
TIMEOUT = 5


def send(tokens: list[str], title: str, body: str, data: dict) -> list[str]:
    """보낸 뒤 더 이상 쓸 수 없는 토큰(DeviceNotRegistered) 목록을 돌려준다."""
    if not tokens or not settings.PUSH_ENABLED:
        return []
    messages = [{"to": t, "title": title, "body": body, "data": data, "sound": "default"} for t in tokens]
    try:
        resp = requests.post(EXPO_PUSH_URL, json=messages, timeout=TIMEOUT)
        resp.raise_for_status()
        tickets = resp.json().get("data", [])
    except (requests.RequestException, ValueError):
        logger.warning("푸시 전송 실패", exc_info=True)
        return []
    dead = []
    for token, ticket in zip(tokens, tickets):
        if ticket.get("status") == "error" and ticket.get("details", {}).get("error") == "DeviceNotRegistered":
            dead.append(token)
    return dead
