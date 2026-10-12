from django.utils import timezone
from rest_framework import serializers

from community.serializers import AuthorSerializer
from pets.models import Pet

from .models import Gathering, Participation


class PetBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = ["id", "name", "species", "breed", "size", "weight_kg"]


class ParticipationSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)
    pet = PetBriefSerializer(read_only=True)

    class Meta:
        model = Participation
        fields = ["id", "user", "pet", "message", "status", "created_at", "decided_at"]


class GatheringSerializer(serializers.ModelSerializer):
    host = AuthorSerializer(read_only=True)
    accepted_count = serializers.IntegerField(source="n_accepted", read_only=True)
    participants = serializers.SerializerMethodField()
    my_participation = serializers.SerializerMethodField()
    is_host = serializers.SerializerMethodField()

    class Meta:
        model = Gathering
        fields = [
            "id",
            "host",
            "kind",
            "species",
            "region_name",
            "title",
            "content",
            "place_name",
            "starts_at",
            "capacity",
            "status",
            "accepted_count",
            "participants",
            "my_participation",
            "is_host",
            "is_hidden",
            "created_at",
        ]
        read_only_fields = ["id", "region_name", "is_hidden", "created_at"]

    def _user(self):
        return self.context["request"].user

    def get_participants(self, obj) -> list[dict]:
        accepted = [p for p in obj.participations.all() if p.status == Participation.Status.ACCEPTED]
        return ParticipationSerializer(accepted, many=True).data

    def get_my_participation(self, obj) -> dict | None:
        mine = next((p for p in obj.participations.all() if p.user_id == self._user().id), None)
        return ParticipationSerializer(mine).data if mine else None

    def get_is_host(self, obj) -> bool:
        return obj.host_id == self._user().id

    def validate_capacity(self, value):
        if not 1 <= value <= 20:
            raise serializers.ValidationError("인원은 1~20명으로 정해 주세요.")
        return value

    def validate_starts_at(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("지난 시간으로는 모임을 만들 수 없어요.")
        return value

    def validate_status(self, value):
        # 모임장이 바꿀 수 있는 건 '취소'뿐. 마감·모집 중은 인원에 따라 자동.
        if self.instance is None or value not in (Gathering.Status.CANCELLED, self.instance.status):
            raise serializers.ValidationError("모임 상태는 취소만 직접 바꿀 수 있어요.")
        return value

    def validate(self, attrs):
        if self.instance is not None and "capacity" in attrs:
            if attrs["capacity"] < self.instance.count_accepted():
                raise serializers.ValidationError({"capacity": "이미 수락한 인원보다 적게 줄일 수 없어요."})
        return attrs


class ApplySerializer(serializers.Serializer):
    pet = serializers.IntegerField(required=False, allow_null=True)
    message = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")

    def validate_pet(self, value):
        if value is None:
            return None
        pet = Pet.objects.filter(pk=value, user=self.context["request"].user).first()
        if pet is None:
            raise serializers.ValidationError("내 반려동물이 아니에요.")
        return pet
