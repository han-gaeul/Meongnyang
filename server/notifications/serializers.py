from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    path = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "path", "read_at", "created_at"]

    def get_path(self, obj) -> str:
        return obj.data.get("path", "")


class DeviceTokenSerializer(serializers.Serializer):
    token = serializers.RegexField(r"^(Exponent|Expo)PushToken\[[^\]]+\]$", max_length=200)
    platform = serializers.ChoiceField(choices=["ios", "android", "web"], required=False, default="")


class UnreadSerializer(serializers.Serializer):
    notifications = serializers.IntegerField()
    messages = serializers.IntegerField()
