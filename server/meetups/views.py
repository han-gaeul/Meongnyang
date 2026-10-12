from django.conf import settings
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsVerifiedMember

from . import services


class LocationSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)


class TokenRequestSerializer(LocationSerializer):
    gathering = serializers.IntegerField(required=False, allow_null=True)


class TokenResponseSerializer(serializers.Serializer):
    qr = serializers.CharField()
    expires_in = serializers.IntegerField()


class ConfirmRequestSerializer(LocationSerializer):
    qr = serializers.CharField(max_length=2000)


class NeighborSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nickname = serializers.CharField()
    meet_count = serializers.IntegerField()
    last_met_on = serializers.DateField()
    level = serializers.ChoiceField(choices=["none", "neighbor", "regular"])


class ConfirmResponseSerializer(serializers.Serializer):
    created = serializers.BooleanField()
    neighbor = NeighborSerializer()


def _neighbor(user, other_id) -> dict:
    other = get_user_model().objects.get(pk=other_id)
    stats = next(n for n in services.neighbors_of(user) if n["user_id"] == other_id)
    return {
        "id": other.id,
        "nickname": other.nickname,
        "meet_count": stats["count"],
        "last_met_on": stats["last_met_on"],
        "level": stats["level"],
    }


class MeetupTokenView(APIView):
    """내 QR 띄우기. 몇 분 동안만 유효하다."""

    permission_classes = [IsVerifiedMember]

    @extend_schema(request=TokenRequestSerializer, responses={200: TokenResponseSerializer})
    def post(self, request):
        s = TokenRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        qr = services.issue_token(request.user, s.validated_data["lat"], s.validated_data["lng"], s.validated_data.get("gathering"))
        return Response({"qr": qr, "expires_in": settings.MEETUP_TOKEN_TTL})


class MeetupConfirmView(APIView):
    """상대 QR을 찍어 만남 인증"""

    permission_classes = [IsVerifiedMember]
    throttle_scope = "meetup"

    @extend_schema(request=ConfirmRequestSerializer, responses={200: ConfirmResponseSerializer})
    def post(self, request):
        s = ConfirmRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            result = services.confirm(request.user, s.validated_data["qr"], s.validated_data["lat"], s.validated_data["lng"])
        except services.MeetupError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=400)
        return Response({"created": result.created, "neighbor": _neighbor(request.user, result.other_id)})


class NeighborListView(APIView):
    """만난 이웃 목록 (만남 많은 순)"""

    @extend_schema(responses={200: NeighborSerializer(many=True)})
    def get(self, request):
        stats = services.neighbors_of(request.user)
        users = get_user_model().objects.in_bulk([n["user_id"] for n in stats])
        rows = [
            {
                "id": n["user_id"],
                "nickname": users[n["user_id"]].nickname,
                "meet_count": n["count"],
                "last_met_on": n["last_met_on"],
                "level": n["level"],
            }
            for n in stats
            if n["user_id"] in users and users[n["user_id"]].is_active
        ]
        rows.sort(key=lambda r: (-r["meet_count"], r["nickname"]))
        return Response(NeighborSerializer(rows, many=True).data)
