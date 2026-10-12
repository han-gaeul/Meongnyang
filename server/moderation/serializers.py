from rest_framework import serializers

from .models import Report


class ReportCreateSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=Report.Reason.choices)
    detail = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class ReportResultSerializer(serializers.Serializer):
    created = serializers.BooleanField()
    hidden = serializers.BooleanField()
