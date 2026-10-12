from rest_framework import serializers

from .models import Pet


class PetSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Pet
        fields = [
            "id",
            "user",
            "name",
            "species",
            "breed",
            "sex",
            "birthday",
            "age",
            "neutered",
            "vaccinated",
            "size",
            "weight_kg",
            "traits",
            "verification_status",
            "created_at",
            "updated_at",
        ]
        # 인증 상태와 소유자는 서버만 바꾼다. 등록번호는 응답에 넣지 않는다.
        read_only_fields = ["id", "user", "verification_status", "created_at", "updated_at"]

    def validate_traits(self, value):
        if not isinstance(value, list) or not all(isinstance(t, str) for t in value):
            raise serializers.ValidationError("성격 태그는 문자열 목록이어야 합니다.")
        if len(value) > 10:
            raise serializers.ValidationError("성격 태그는 10개까지 넣을 수 있습니다.")
        return value


class PetVerifySerializer(serializers.Serializer):
    registration_number = serializers.RegexField(
        r"^\d{15}$", error_messages={"invalid": "동물등록번호는 숫자 15자리입니다."}
    )
