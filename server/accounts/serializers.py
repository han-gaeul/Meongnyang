from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["email", "password", "nickname"]
        extra_kwargs = {"email": {"required": True, "allow_null": False}}

    def validate(self, attrs):
        validate_password(attrs["password"], User(email=attrs["email"], nickname=attrs["nickname"]))
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


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


class IdentityVerifySerializer(serializers.Serializer):
    transaction_id = serializers.CharField(max_length=100)


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    created = serializers.BooleanField(required=False)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
