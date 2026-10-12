from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from community.serializers import AuthorSerializer
from gatherings.serializers import PetBriefSerializer
from pets.models import Pet

from . import services
from .models import Favor, FavorApplication, FavorThanks

MIN_MINUTES, MAX_MINUTES = 10, 120  # 1차 출시: 짧은 부탁만
MAX_DAYS_AHEAD = 30


# ---- 돌봄 시트 ----

class MealSerializer(serializers.Serializer):
    times_per_day = serializers.IntegerField(min_value=0, max_value=10, allow_null=True, required=False)
    amount = serializers.CharField(max_length=50, allow_blank=True, required=False, default="")
    food = serializers.CharField(max_length=50, allow_blank=True, required=False, default="")


class MedSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    dose = serializers.CharField(max_length=50, allow_blank=True, required=False, default="")
    time = serializers.CharField(max_length=50, allow_blank=True, required=False, default="")


class WalkSerializer(serializers.Serializer):
    minutes = serializers.IntegerField(min_value=0, max_value=600, allow_null=True, required=False)
    per_week = serializers.IntegerField(min_value=0, max_value=50, allow_null=True, required=False)


class BasicInfoSerializer(serializers.Serializer):
    name = serializers.CharField()
    species = serializers.CharField()
    breed = serializers.CharField(allow_blank=True)
    sex = serializers.CharField(allow_blank=True)
    age = serializers.IntegerField(allow_null=True)
    size = serializers.CharField(allow_blank=True)
    weight_kg = serializers.FloatField(allow_null=True)
    neutered = serializers.BooleanField(allow_null=True)
    vaccinated = serializers.BooleanField(allow_null=True)
    traits = serializers.ListField(child=serializers.CharField())


class CareSheetInputSerializer(serializers.Serializer):
    """보호자가 확인·수정해서 올리는 돌봄 시트. 기본 정보는 서버가 반려동물 프로필로 채운다."""

    meal = MealSerializer(required=False)
    meds = MedSerializer(many=True, required=False)
    condition = serializers.CharField(max_length=200, allow_blank=True, required=False, default="")
    walk = WalkSerializer(required=False)
    notes = serializers.CharField(max_length=500, allow_blank=True, required=False, default="")
    caution = serializers.CharField(max_length=500, allow_blank=True, required=False, default="")

    def validate_meds(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("약은 10개까지 적을 수 있어요.")
        return value


class CareSheetSourceSerializer(serializers.Serializer):
    days = serializers.IntegerField()
    from_journal = serializers.ListField(child=serializers.CharField(), help_text="일기에서 채운 항목")


class CareSheetSerializer(CareSheetInputSerializer):
    basic = BasicInfoSerializer()


class CareSheetDraftSerializer(CareSheetSerializer):
    source = CareSheetSourceSerializer()


class CareSummarySerializer(serializers.Serializer):
    species = serializers.CharField(allow_null=True)
    breed = serializers.CharField(allow_blank=True)
    size = serializers.CharField(allow_blank=True)
    age = serializers.IntegerField(allow_null=True)
    traits = serializers.ListField(child=serializers.CharField())
    walk = WalkSerializer()


# ---- 부탁 ----

class FavorApplicationSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)

    class Meta:
        model = FavorApplication
        fields = ["id", "user", "message", "status", "agreed_at", "created_at", "decided_at"]


class FavorThanksSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavorThanks
        fields = ["message", "created_at"]


class FavorSerializer(serializers.ModelSerializer):
    requester = AuthorSerializer(read_only=True)
    helper = AuthorSerializer(read_only=True)
    pet = PetBriefSerializer(read_only=True)
    pet_id = serializers.PrimaryKeyRelatedField(source="pet", queryset=Pet.objects.all(), write_only=True)
    care_sheet = serializers.SerializerMethodField()
    care_sheet_input = CareSheetInputSerializer(write_only=True, required=False)
    care_summary = serializers.SerializerMethodField()
    agree_terms = serializers.BooleanField(write_only=True, required=False)
    is_requester = serializers.SerializerMethodField()
    my_application = serializers.SerializerMethodField()
    can_help = serializers.SerializerMethodField()
    cannot_help_reason = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()
    thanks = FavorThanksSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Favor
        fields = [
            "id",
            "requester",
            "pet",
            "pet_id",
            "kind",
            "visit_home",
            "region_name",
            "title",
            "content",
            "place_name",
            "starts_at",
            "duration_minutes",
            "care_summary",
            "care_sheet",
            "care_sheet_input",
            "agree_terms",
            "status",
            "helper",
            "matched_at",
            "completed_at",
            "is_requester",
            "my_application",
            "can_help",
            "cannot_help_reason",
            "pending_count",
            "thanks",
            "is_hidden",
            "created_at",
        ]
        read_only_fields = [
            "id", "region_name", "status", "matched_at", "completed_at", "is_hidden", "created_at",
        ]

    def _user(self):
        return self.context["request"].user

    def _eligibility(self, obj):
        cache = self.context.setdefault("_elig", {})
        if obj.pk not in cache:
            cache[obj.pk] = services.can_help(self._user(), obj)
        return cache[obj.pk]

    def _can_see_sheet(self, obj) -> bool:
        uid = self._user().id
        return uid == obj.requester_id or (uid == obj.helper_id and obj.status in ("matched", "done"))

    @staticmethod
    def _summary(obj) -> dict:
        return services.care_summary(obj.care_sheet)

    def get_care_summary(self, obj) -> CareSummarySerializer:
        return self._summary(obj)

    def get_care_sheet(self, obj) -> CareSheetSerializer(allow_null=True):
        """전체 돌봄 시트: 보호자와 맡은 이웃에게만"""
        return obj.care_sheet if self._can_see_sheet(obj) else None

    def get_is_requester(self, obj) -> bool:
        return obj.requester_id == self._user().id

    def get_my_application(self, obj) -> FavorApplicationSerializer(allow_null=True):
        mine = next((a for a in obj.applications.all() if a.user_id == self._user().id), None)
        return FavorApplicationSerializer(mine).data if mine else None

    def get_can_help(self, obj) -> bool:
        return obj.requester_id != self._user().id and self._eligibility(obj).ok

    def get_cannot_help_reason(self, obj) -> str:
        if obj.requester_id == self._user().id:
            return ""
        return self._eligibility(obj).reason

    def get_pending_count(self, obj) -> int | None:
        """보호자에게만: 대기 중인 신청 수"""
        if obj.requester_id != self._user().id:
            return None
        return sum(1 for a in obj.applications.all() if a.status == FavorApplication.Status.PENDING)

    # ---- 검증 ----

    def validate_pet_id(self, pet):
        if pet.user_id != self._user().id:
            raise serializers.ValidationError("내 반려동물이 아니에요.")
        if pet.verification_status != Pet.Verification.APPROVED:
            raise serializers.ValidationError("인증을 마친 반려동물만 부탁할 수 있어요.")
        return pet

    def validate_duration_minutes(self, value):
        if not MIN_MINUTES <= value <= MAX_MINUTES:
            raise serializers.ValidationError(f"지금은 {MIN_MINUTES}분~{MAX_MINUTES // 60}시간 이내의 짧은 부탁만 할 수 있어요.")
        return value

    def validate_starts_at(self, value):
        now = timezone.now()
        if value < now:
            raise serializers.ValidationError("지난 시간으로는 부탁할 수 없어요.")
        if value > now + timedelta(days=MAX_DAYS_AHEAD):
            raise serializers.ValidationError(f"{MAX_DAYS_AHEAD}일 이내 일정만 올릴 수 있어요.")
        return value

    def validate(self, attrs):
        if self.instance is None:
            if attrs.get("agree_terms") is not True:
                raise serializers.ValidationError({"agree_terms": "책임 범위와 사고 처리 원칙에 동의해 주세요."})
            if not attrs.get("visit_home") and not attrs.get("place_name"):
                raise serializers.ValidationError({"place_name": "만날 곳을 적어 주세요."})
        elif self.instance.status != Favor.Status.OPEN:
            raise serializers.ValidationError("약속이 잡힌 뒤에는 고칠 수 없어요.")
        elif "pet" in attrs and attrs["pet"] != self.instance.pet:
            raise serializers.ValidationError({"pet_id": "반려동물은 바꿀 수 없어요. 새로 올려 주세요."})
        return attrs

    def _sheet(self, pet, sheet_input: dict | None, current: dict | None = None) -> dict:
        base = dict(current or services.draft_care_sheet(pet))
        base.pop("source", None)
        if sheet_input:
            base.update(sheet_input)
        base["basic"] = services.basic_info(pet)
        return base

    def create(self, validated):
        validated.pop("agree_terms", None)
        sheet_input = validated.pop("care_sheet_input", None)
        validated["care_sheet"] = self._sheet(validated["pet"], sheet_input)
        validated["requester_agreed_at"] = timezone.now()
        return super().create(validated)

    def update(self, instance, validated):
        validated.pop("agree_terms", None)
        sheet_input = validated.pop("care_sheet_input", None)
        if sheet_input is not None:
            validated["care_sheet"] = self._sheet(instance.pet, sheet_input, instance.care_sheet)
        return super().update(instance, validated)


class FavorApplySerializer(serializers.Serializer):
    message = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    agree_terms = serializers.BooleanField()

    def validate_agree_terms(self, value):
        if value is not True:
            raise serializers.ValidationError("책임 범위와 사고 처리 원칙에 동의해 주세요.")
        return value


class FavorThanksCreateSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=300)
