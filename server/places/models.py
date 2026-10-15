"""자체 장소 DB.

공식 데이터(인허가·TourAPI)와 사용자 제보로 채우고, 화면은 카카오맵으로 보여준다.
"애견 동반 가능" 한 줄 대신 동반 조건을 구조화해 두고, 실제 방문 후기(함께 간
반려동물의 크기·체중이 붙음)로 조건을 보강하는 것이 이 앱의 차별점이다.
"""

from django.conf import settings
from django.db import models

from common.models import Moderated


class Place(models.Model):
    class Category(models.TextChoices):
        CAFE = "cafe", "카페"
        RESTAURANT = "restaurant", "식당"
        STAY = "stay", "숙소"
        ATTRACTION = "attraction", "관광지"
        PARK = "park", "공원·운동장"
        HOSPITAL = "hospital", "동물병원"
        PHARMACY = "pharmacy", "동물약국"
        GROOMING = "grooming", "미용"
        HOTEL = "hotel", "위탁·호텔"
        ETC = "etc", "기타"

    class Status(models.TextChoices):
        PENDING = "pending", "검토 대기"  # 사용자 제보 → 운영자 확인 후 게시
        APPROVED = "approved", "게시"
        CLOSED = "closed", "폐업·비공개"

    class Source(models.TextChoices):
        USER = "user", "사용자 제보"
        PUBLIC = "public", "인허가 공공데이터"
        TOURAPI = "tourapi", "한국관광공사"
        KAKAO = "kakao", "카카오 로컬"
        OWNER = "owner", "업주"
        DEV = "dev", "개발용 샘플"

    class Space(models.TextChoices):
        INDOOR = "indoor", "실내 가능"
        OUTDOOR = "outdoor", "테라스·야외만"
        SEPARATE = "separate", "전용 공간"

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=12, choices=Category.choices, db_index=True)
    address = models.CharField(max_length=200, blank=True)
    lat = models.FloatField()
    lng = models.FloatField()
    phone = models.CharField(max_length=30, blank=True)
    region_name = models.CharField(max_length=50, blank=True, db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.USER)
    source_id = models.CharField(max_length=100, blank=True, help_text="원본 데이터의 id (중복 방지)")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="submitted_places"
    )

    # 외부 연결
    kakao_place_id = models.CharField(max_length=30, blank=True)
    naver_place_url = models.URLField(blank=True)
    naver_booking_url = models.URLField(blank=True, help_text="네이버 예약 페이지")

    # 진료·영업
    is_24h = models.BooleanField(default=False)
    hours = models.CharField(max_length=200, blank=True, help_text="예: 매일 10:00-21:00, 월 휴무")

    # 동반 조건 (공식·제보·업주가 밝힌 정책). 모르면 비워 둔다(None).
    sizes_allowed = models.JSONField(default=list, blank=True, help_text='허용 크기 ["S","M","L"]')
    max_weight_kg = models.PositiveSmallIntegerField(null=True, blank=True)
    space = models.CharField(max_length=10, choices=Space.choices, blank=True)
    floor_ok = models.BooleanField(null=True, blank=True, help_text="바닥에 내려놔도 됨 (False면 안기·켄넬·유모차 필수)")
    max_pets = models.PositiveSmallIntegerField(null=True, blank=True)
    restricted_breeds = models.CharField(max_length=200, blank=True)
    fee_per_pet = models.PositiveIntegerField(null=True, blank=True, help_text="1마리당 추가 요금(원), 0이면 없음")
    cats_ok = models.BooleanField(null=True, blank=True)
    amenities = models.JSONField(default=list, blank=True, help_text="water/pet_menu/parking/playground/yard/shower/bed")
    policy_checked_at = models.DateTimeField(null=True, blank=True, help_text="동반 조건을 마지막으로 확인한 때")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["lat", "lng"])]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_id"], condition=~models.Q(source_id=""), name="uniq_place_source"
            )
        ]

    def __str__(self):
        return self.name


class PlaceReview(Moderated):
    """30초 후기. 자유 글 대신 동반 조건을 체크하고, 함께 간 반려동물 크기·체중이 붙는다."""

    class Answer(models.TextChoices):
        YES = "yes", "예"
        NO = "no", "아니요"

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="place_reviews")
    pet = models.ForeignKey("pets.Pet", on_delete=models.SET_NULL, null=True, blank=True)
    # 작성 시점 반려동물 스냅샷 (반려동물 정보를 고쳐도 후기는 그대로)
    pet_species = models.CharField(max_length=3)
    pet_size = models.CharField(max_length=1, blank=True)
    pet_weight_kg = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    visited_on = models.DateField()
    admitted = models.BooleanField(help_text="함께 들어갈 수 있었나")
    space = models.CharField(max_length=10, choices=Place.Space.choices, blank=True)
    floor_ok = models.BooleanField(null=True, blank=True)
    extra_fee = models.BooleanField(null=True, blank=True)
    comment = models.CharField(max_length=300, blank=True)
    verified_visit = models.BooleanField(default=False, help_text="장소 근처에서 작성")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-visited_on", "-id"]


class ReviewImage(models.Model):
    """입구 안내문·메뉴판 사진 같은 근거"""

    review = models.ForeignKey(PlaceReview, on_delete=models.CASCADE, related_name="review_images")
    image = models.OneToOneField("uploads.UploadedImage", on_delete=models.CASCADE, related_name="review_image")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
