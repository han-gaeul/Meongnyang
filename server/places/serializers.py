from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from community.serializers import AuthorSerializer
from pets.models import Pet
from uploads.models import UploadedImage
from uploads.serializers import ImageSerializer

from . import services
from .models import Place, PlaceReview, ReviewImage

AMENITIES = ["water", "pet_menu", "parking", "playground", "yard", "shower", "bed"]


class ConditionsSerializer(serializers.Serializer):
    large_ok = serializers.BooleanField(allow_null=True)
    space = serializers.CharField(allow_blank=True)
    floor_ok = serializers.BooleanField(allow_null=True)
    extra_fee = serializers.BooleanField(allow_null=True)
    review_count = serializers.IntegerField()
    large_reviews = serializers.IntegerField()
    max_weight_admitted = serializers.FloatField(allow_null=True)
    last_checked = serializers.DateTimeField(allow_null=True)
    differs_from_policy = serializers.BooleanField()


class LinksSerializer(serializers.Serializer):
    view = serializers.URLField()
    directions = serializers.URLField()


class PlaceSerializer(serializers.ModelSerializer):
    """목록·상세 공통. 거리·조건·내 반려동물 적합도는 뷰가 context로 넘긴다."""

    distance_m = serializers.SerializerMethodField()
    conditions = serializers.SerializerMethodField()
    fit = serializers.SerializerMethodField()
    kakao = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = [
            "id",
            "name",
            "category",
            "address",
            "lat",
            "lng",
            "phone",
            "region_name",
            "status",
            "source",
            "naver_booking_url",
            "naver_place_url",
            "is_24h",
            "hours",
            "sizes_allowed",
            "max_weight_kg",
            "space",
            "floor_ok",
            "max_pets",
            "restricted_breeds",
            "fee_per_pet",
            "cats_ok",
            "amenities",
            "policy_checked_at",
            "distance_m",
            "conditions",
            "fit",
            "kakao",
            "is_mine",
        ]
        read_only_fields = fields

    def _cond(self, obj) -> services.Conditions:
        cache = self.context.setdefault("_cond", {})
        if obj.pk not in cache:
            reviews = [r for r in obj.reviews.all() if not r.is_hidden]
            cache[obj.pk] = services.conditions(obj, reviews)
        return cache[obj.pk]

    def get_distance_m(self, obj) -> int | None:
        d = self.context.get("distances", {}).get(obj.pk)
        return round(d) if d is not None else None

    def get_conditions(self, obj) -> ConditionsSerializer:
        c = self._cond(obj)
        return ConditionsSerializer(c).data

    def get_fit(self, obj) -> str:
        """선택한 반려동물(?pet=) 기준: yes / no / unknown"""
        return services.fit_for(self.context.get("pet"), obj, self._cond(obj))

    def get_kakao(self, obj) -> LinksSerializer:
        return services.kakao_links(obj)

    def get_is_mine(self, obj) -> bool:
        return obj.created_by_id == self.context["request"].user.id


class PlaceSubmitSerializer(serializers.ModelSerializer):
    """사용자 제보. 운영자 확인 후 지도에 게시된다."""

    class Meta:
        model = Place
        fields = [
            "name",
            "category",
            "address",
            "lat",
            "lng",
            "phone",
            "region_name",
            "naver_booking_url",
            "is_24h",
            "hours",
            "sizes_allowed",
            "max_weight_kg",
            "space",
            "floor_ok",
            "max_pets",
            "fee_per_pet",
            "cats_ok",
            "amenities",
        ]
        extra_kwargs = {"region_name": {"required": False}}

    def validate_lat(self, v):
        if not 33 <= v <= 39:
            raise serializers.ValidationError("국내 위치만 등록할 수 있어요.")
        return v

    def validate_lng(self, v):
        if not 124 <= v <= 132:
            raise serializers.ValidationError("국내 위치만 등록할 수 있어요.")
        return v

    def validate_sizes_allowed(self, v):
        if not isinstance(v, list) or any(s not in ("S", "M", "L") for s in v):
            raise serializers.ValidationError("크기는 S, M, L 중에서 골라 주세요.")
        return sorted(set(v), key="SML".index)

    def validate_amenities(self, v):
        if not isinstance(v, list) or any(a not in AMENITIES for a in v):
            raise serializers.ValidationError(f"편의시설은 {', '.join(AMENITIES)} 중에서 골라 주세요.")
        return list(dict.fromkeys(v))

    def create(self, validated):
        policy_given = any(
            validated.get(k) not in (None, "", [])
            for k in ("sizes_allowed", "max_weight_kg", "space", "floor_ok", "fee_per_pet")
        )
        if policy_given:
            validated["policy_checked_at"] = timezone.now()
        return super().create(validated)


class ReviewSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)
    images = serializers.SerializerMethodField()
    pet_id = serializers.PrimaryKeyRelatedField(source="pet", queryset=Pet.objects.all(), write_only=True)
    image_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False, max_length=3)
    lat = serializers.FloatField(write_only=True, required=False, help_text="방문 확인용 현재 위치(저장 안 함)")
    lng = serializers.FloatField(write_only=True, required=False)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = PlaceReview
        fields = [
            "id",
            "user",
            "pet_id",
            "pet_species",
            "pet_size",
            "pet_weight_kg",
            "visited_on",
            "admitted",
            "space",
            "floor_ok",
            "extra_fee",
            "comment",
            "verified_visit",
            "images",
            "image_ids",
            "lat",
            "lng",
            "is_mine",
            "is_hidden",
            "created_at",
        ]
        read_only_fields = [
            "id", "pet_species", "pet_size", "pet_weight_kg", "verified_visit", "is_hidden", "created_at",
        ]

    def get_images(self, obj) -> ImageSerializer(many=True):
        return ImageSerializer([ri.image for ri in obj.review_images.all()], many=True, context=self.context).data

    def get_is_mine(self, obj) -> bool:
        return obj.user_id == self.context["request"].user.id

    def validate_pet_id(self, pet):
        if pet.user_id != self.context["request"].user.id:
            raise serializers.ValidationError("내 반려동물이 아니에요.")
        return pet

    def validate_visited_on(self, v):
        today = timezone.localdate()
        if v > today:
            raise serializers.ValidationError("아직 오지 않은 날이에요.")
        if (today - v).days > 365:
            raise serializers.ValidationError("1년 안에 다녀온 곳만 남길 수 있어요.")
        return v

    def validate_image_ids(self, value):
        user = self.context["request"].user
        images = {
            i.id: i
            for i in UploadedImage.objects.filter(id__in=value, owner=user).select_related("review_image", "post_image")
        }
        out = []
        for image_id in dict.fromkeys(value):
            img = images.get(image_id)
            if img is None:
                raise serializers.ValidationError("올리지 않았거나 다른 사람의 사진입니다.")
            if getattr(img, "review_image", None) or getattr(img, "post_image", None):
                raise serializers.ValidationError("이미 다른 곳에 사용된 사진입니다.")
            out.append(img)
        return out

    @transaction.atomic
    def create(self, validated):
        images = validated.pop("image_ids", [])
        lat, lng = validated.pop("lat", None), validated.pop("lng", None)
        pet = validated["pet"]
        place = validated["place"]
        review = PlaceReview.objects.create(
            **validated,
            pet_species=pet.species,
            pet_size=pet.size,
            pet_weight_kg=pet.weight_kg,
            verified_visit=services.is_visit(place, lat, lng),
        )
        for order, img in enumerate(images):
            ReviewImage.objects.create(review=review, image=img, order=order)
        return review
