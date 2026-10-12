from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 10 * 1024 * 1024
MAX_SIDE = 2048


class InvalidImage(Exception):
    pass


def normalize_image(upload) -> tuple[ContentFile, int, int]:
    """업로드 이미지를 검증하고 JPEG로 다시 저장한다.

    - 이미지가 아닌 파일, 10MB 초과는 거부
    - 회전 정보(EXIF) 반영 후 메타데이터 제거 → 사진 속 위치 정보가 남지 않게
    - 긴 변 2048px로 축소
    """
    if upload.size > MAX_BYTES:
        raise InvalidImage("이미지는 10MB 이하만 올릴 수 있습니다.")
    try:
        with Image.open(upload) as img:
            img.verify()
        upload.seek(0)
        with Image.open(upload) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.thumbnail((MAX_SIDE, MAX_SIDE))
            out = BytesIO()
            img.save(out, format="JPEG", quality=85, optimize=True)
            return ContentFile(out.getvalue(), name="image.jpg"), img.width, img.height
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidImage("이미지 파일이 아니거나 손상되었습니다.") from exc
