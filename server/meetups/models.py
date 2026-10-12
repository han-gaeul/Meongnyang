from django.conf import settings
from django.db import models


class Meetup(models.Model):
    """두 사람이 실제로 만났다는 기록. 같은 두 사람은 하루 1회만 센다.

    개인정보 최소화: 좌표는 저장하지 않고 확인 당시 두 기기 사이 거리만 남긴다.
    user_a는 항상 id가 작은 쪽 (쌍을 한 행으로 유지).
    """

    user_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    user_b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    gathering = models.ForeignKey(
        "gatherings.Gathering", on_delete=models.SET_NULL, null=True, blank=True, related_name="meetups"
    )
    met_on = models.DateField()
    distance_m = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-met_on", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["user_a", "user_b", "met_on"], name="uniq_meetup_per_day"),
            models.CheckConstraint(condition=models.Q(user_a__lt=models.F("user_b")), name="meetup_ordered_pair"),
        ]
