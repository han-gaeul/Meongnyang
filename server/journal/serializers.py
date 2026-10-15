from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from favors.serializers import MedSerializer
from pets.models import Pet
from uploads.models import UploadedImage
from uploads.serializers import ImageSerializer

from . import services
from .models import JournalEntry, JournalImage


class JournalEntrySerializer(serializers.ModelSerializer):
    pet_id = serializers.PrimaryKeyRelatedField(source="pet", queryset=Pet.objects.all())
    images = serializers.SerializerMethodField()
    image_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False, max_length=5)
    meds = MedSerializer(many=True, required=False, allow_null=True)
    route = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2),
        required=False,
        max_length=services.MAX_ROUTE_POINTS,
    )

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "pet_id",
            "kind",
            "date",
            "title",
            "content",
            "share_in_care_sheet",
            "started_at",
            "ended_at",
            "duration_sec",
            "distance_m",
            "route",
            "meals_per_day",
            "meal_amount",
            "food",
            "vitality",
            "meds",
            "weight_kg",
            "images",
            "image_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_images(self, obj) -> ImageSerializer(many=True):
        return ImageSerializer([ji.image for ji in obj.entry_images.all()], many=True, context=self.context).data

    def _user(self):
        return self.context["request"].user

    def validate_pet_id(self, pet):
        if pet.user_id != self._user().id:
            raise serializers.ValidationError("내 반려동물이 아니에요.")
        return pet

    def validate_date(self, v):
        if v > timezone.localdate():
            raise serializers.ValidationError("아직 오지 않은 날이에요.")
        return v

    def validate_vitality(self, v):
        if v is not None and not 1 <= v <= 5:
            raise serializers.ValidationError("활력은 1~5로 골라 주세요.")
        return v

    def validate_meals_per_day(self, v):
        if v is not None and v > 10:
            raise serializers.ValidationError("하루 10번까지 적을 수 있어요.")
        return v

    def validate_route(self, route):
        for lat, lng in route:
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise serializers.ValidationError("좌표가 올바르지 않아요.")
        return [[round(lat, 6), round(lng, 6)] for lat, lng in route]

    def validate_image_ids(self, value):
        images = {
            i.id: i
            for i in UploadedImage.objects.filter(id__in=value, owner=self._user()).select_related(
                "journal_image", "post_image", "review_image"
            )
        }
        out = []
        for image_id in dict.fromkeys(value):
            img = images.get(image_id)
            if img is None:
                raise serializers.ValidationError("올리지 않았거나 다른 사람의 사진입니다.")
            attached = getattr(img, "journal_image", None)
            if getattr(img, "post_image", None) or getattr(img, "review_image", None) or (
                attached and (self.instance is None or attached.entry_id != self.instance.id)
            ):
                raise serializers.ValidationError("이미 다른 곳에 사용된 사진입니다.")
            out.append(img)
        return out

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        if self.instance is not None and "kind" in attrs and attrs["kind"] != self.instance.kind:
            raise serializers.ValidationError({"kind": "일기 종류는 바꿀 수 없어요."})
        get = lambda k: attrs.get(k, getattr(self.instance, k, None))  # noqa: E731

        if kind == JournalEntry.Kind.WALK:
            started, ended = get("started_at"), get("ended_at")
            if started and ended:
                if ended <= started:
                    raise serializers.ValidationError({"ended_at": "끝난 시간이 시작보다 빨라요."})
                if ended - started > timedelta(hours=12):
                    raise serializers.ValidationError({"ended_at": "산책은 12시간까지 기록할 수 있어요."})
                attrs.setdefault("duration_sec", int((ended - started).total_seconds()))
            if not get("duration_sec"):
                raise serializers.ValidationError({"duration_sec": "산책 시간을 알려 주세요."})
            if "route" in attrs and len(attrs["route"]) >= 2:
                attrs["route"] = services.simplify(attrs["route"])
                attrs["distance_m"] = services.route_length_m(attrs["route"])
        elif kind == JournalEntry.Kind.HEALTH:
            values = [get(f) for f in ("meals_per_day", "meal_amount", "food", "vitality", "weight_kg", "content")]
            if all(v in (None, "") for v in values) and get("meds") is None:
                raise serializers.ValidationError("식사·활력·약·체중 중 하나는 적어 주세요.")
        elif kind == JournalEntry.Kind.DAILY:
            if not (get("content") or "").strip() and not attrs.get("image_ids") and not get("title"):
                raise serializers.ValidationError({"content": "내용이나 사진을 넣어 주세요."})
        return attrs

    def _set_images(self, entry, images):
        JournalImage.objects.filter(entry=entry).exclude(image__in=images).delete()
        for order, img in enumerate(images):
            JournalImage.objects.update_or_create(image=img, defaults={"entry": entry, "order": order})

    @transaction.atomic
    def create(self, validated):
        images = validated.pop("image_ids", [])
        entry = JournalEntry.objects.create(**validated)
        self._set_images(entry, images)
        return entry

    @transaction.atomic
    def update(self, instance, validated):
        images = validated.pop("image_ids", None)
        instance = super().update(instance, validated)
        if images is not None:
            self._set_images(instance, images)
        return instance


class CalendarDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    kinds = serializers.ListField(child=serializers.ChoiceField(choices=JournalEntry.Kind.choices))
    walk_minutes = serializers.IntegerField()
    count = serializers.IntegerField()
