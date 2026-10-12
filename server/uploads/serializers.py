from rest_framework import serializers

from .models import UploadedImage


class ImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = UploadedImage
        fields = ["id", "url", "width", "height"]

    def get_url(self, obj) -> str:
        url = obj.file.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request and url.startswith("/") else url


class ImageUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
