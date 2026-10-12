import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def _image_path(instance, filename):
    return f"images/{timezone.now():%Y/%m}/{uuid.uuid4().hex}.jpg"


class UploadedImage(models.Model):
    """먼저 올리고, 글·모임글 등을 만들 때 id로 붙인다.

    업로드한 본인만 자기 이미지를 붙일 수 있다. 어디에도 붙지 않은 이미지는
    정리 작업(추후)으로 지운다.
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="images")
    file = models.ImageField(upload_to=_image_path)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now)
