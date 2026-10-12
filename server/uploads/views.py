from drf_spectacular.utils import extend_schema
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsVerifiedMember

from .models import UploadedImage
from .processing import InvalidImage, normalize_image
from .serializers import ImageSerializer, ImageUploadSerializer


class ImageUploadView(APIView):
    """사진 업로드. 인증 회원만. 응답의 id를 글 작성 시 image_ids로 넘긴다."""

    permission_classes = [IsVerifiedMember]
    parser_classes = [MultiPartParser]
    throttle_scope = "upload"

    @extend_schema(request={"multipart/form-data": ImageUploadSerializer}, responses={201: ImageSerializer})
    def post(self, request):
        serializer = ImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            content, width, height = normalize_image(serializer.validated_data["file"])
        except InvalidImage as exc:
            return Response({"detail": str(exc)}, status=400)
        image = UploadedImage(owner=request.user, width=width, height=height)
        image.file.save(content.name, content, save=False)
        image.save()
        return Response(ImageSerializer(image, context={"request": request}).data, status=201)
