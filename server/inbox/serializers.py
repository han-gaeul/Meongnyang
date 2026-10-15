from rest_framework import serializers

from community.serializers import AuthorSerializer

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    sender = AuthorSerializer(read_only=True)
    recipient = AuthorSerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "sender", "recipient", "content", "read_at", "is_mine", "created_at"]

    def get_is_mine(self, obj) -> bool:
        return obj.sender_id == self.context["request"].user.id


class SendSerializer(serializers.Serializer):
    recipient = serializers.IntegerField()
    content = serializers.CharField(max_length=1000)

    def validate_content(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("내용을 적어 주세요.")
        return v


class ThreadSerializer(serializers.Serializer):
    user = AuthorSerializer()
    last = serializers.SerializerMethodField()
    unread = serializers.IntegerField()

    def get_last(self, obj) -> MessageSerializer:
        return MessageSerializer(obj["last"], context=self.context).data


class CanSendSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    reason = serializers.CharField(allow_blank=True)


class WithSerializer(serializers.Serializer):
    user = serializers.IntegerField()
