"""개발·시연용 샘플 장소 (DEBUG에서만). 이름 앞에 [샘플]이 붙는다.

    python manage.py seed_dev_places --lat 37.5556 --lng 126.9019

좌표를 주면 그 주변에 흩어 놓는다(아이폰으로 확인할 때 내 위치 근처에 보이도록).
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from places.models import Place

# (이름, 분류, 북쪽 m, 동쪽 m, 정책)
SAMPLES = [
    ("멍멍 테라스 카페", "cafe", 250, 120, dict(sizes_allowed=["S", "M", "L"], space="outdoor", floor_ok=True, fee_per_pet=0, amenities=["water", "pet_menu"])),
    ("소형견 전용 브런치", "restaurant", -180, 300, dict(sizes_allowed=["S"], max_weight_kg=7, space="indoor", floor_ok=False, fee_per_pet=0)),
    ("대형견 환영 펍", "restaurant", 600, -350, dict(sizes_allowed=["S", "M", "L"], space="indoor", floor_ok=True, fee_per_pet=0, amenities=["water", "parking"])),
    ("한강 반려견 놀이터", "park", -700, -500, dict(sizes_allowed=["S", "M", "L"], amenities=["playground", "water"])),
    ("24시 OO동물의료센터", "hospital", 900, 650, dict(is_24h=True, hours="연중무휴 24시간")),
    ("동네 동물병원", "hospital", -400, 800, dict(hours="평일 10:00-19:00, 토 10:00-15:00")),
    ("펫 스테이 하우스", "stay", 1500, -1200, dict(sizes_allowed=["S", "M"], max_weight_kg=15, fee_per_pet=20000, cats_ok=True, amenities=["yard", "shower", "bed"])),
    ("정보 확인 중인 카페", "cafe", 350, -150, dict()),
]


class Command(BaseCommand):
    help = "개발용 샘플 장소를 만든다 (DEBUG 전용)"

    def add_arguments(self, parser):
        parser.add_argument("--lat", type=float, default=37.5556)
        parser.add_argument("--lng", type=float, default=126.9019)
        parser.add_argument("--clear", action="store_true", help="기존 샘플을 지우고 다시 만든다")

    def handle(self, *args, lat, lng, clear, **opts):
        if not settings.DEBUG:
            raise CommandError("샘플 장소는 DEBUG=True에서만 만들 수 있어요.")
        if clear:
            Place.objects.filter(source=Place.Source.DEV).delete()
        import math

        now = timezone.now()
        made = 0
        for i, (name, cat, north, east, policy) in enumerate(SAMPLES):
            plat = lat + north / 111_320
            plng = lng + east / (111_320 * math.cos(math.radians(lat)))
            policy = dict(policy)
            if any(k in policy for k in ("sizes_allowed", "space", "floor_ok", "fee_per_pet")):
                policy["policy_checked_at"] = now
            _, created = Place.objects.update_or_create(
                source=Place.Source.DEV,
                source_id=f"dev-{i}",
                defaults=dict(name=f"[샘플] {name}", category=cat, lat=plat, lng=plng, status=Place.Status.APPROVED, **policy),
            )
            made += created
        self.stdout.write(self.style.SUCCESS(f"샘플 장소 {len(SAMPLES)}곳 (새로 {made}곳)"))
