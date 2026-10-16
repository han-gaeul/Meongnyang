from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


def check_invite(code: str | None):
    """비공개 베타: 초대 코드가 설정돼 있으면 맞아야 가입된다."""
    from django.conf import settings
    from django.utils.crypto import constant_time_compare

    if settings.INVITE_REQUIRED and not constant_time_compare(code or "", settings.BETA_INVITE_CODE):
        raise serializers.ValidationError({"invite_code": "초대 코드가 맞지 않아요."})


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    invite_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["email", "password", "nickname", "invite_code"]
        extra_kwargs = {"email": {"required": True, "allow_null": False}}

    def validate(self, attrs):
        check_invite(attrs.pop("invite_code", ""))
        validate_password(attrs["password"], User(email=attrs["email"], nickname=attrs["nickname"]))
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class AuthConfigSerializer(serializers.Serializer):
    invite_required = serializers.BooleanField()
    beta = serializers.BooleanField(help_text="본인인증·등록번호 조회가 개발용(mock)인 베타 운영 중")


class MeSerializer(serializers.ModelSerializer):
    is_verified_member = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "nickname",
            "region_name",
            "latitude",
            "longitude",
            "is_identity_verified",
            "is_verified_member",
        ]
        read_only_fields = ["id", "email", "is_identity_verified", "is_verified_member"]


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "nickname", "region_name"]


class SocialLoginSerializer(serializers.Serializer):
    token = serializers.CharField(help_text="카카오·네이버: access token / 구글·애플: id token")
    invite_code = serializers.CharField(required=False, allow_blank=True, help_text="처음 가입할 때만 확인")


class IdentityVerifySerializer(serializers.Serializer):
    transaction_id = serializers.CharField(max_length=100)


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    created = serializers.BooleanField(required=False)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
