from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsOwnerOrReadOnly

from .models import Pet
from .registry import get_pet_registry
from .serializers import PetSerializer, PetVerifySerializer


class PetViewSet(viewsets.ModelViewSet):
    """반려동물. 목록은 `?user=<id>`로 다른 사람 반려동물 조회, 기본은 내 반려동물."""

    serializer_class = PetSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def get_queryset(self):
        qs = Pet.objects.all()
        if self.action == "list":
            user_id = self.request.query_params.get("user")
            qs = qs.filter(user_id=user_id) if user_id else qs.filter(user=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # 인증된 반려동물의 핵심 정보가 바뀌면 다시 인증받게 할 수 있도록 여기서 처리 지점을 둔다.
        serializer.save()

    def get_throttles(self):
        # 인증 요청만 시간당 횟수 제한 (조회 API 비용·남용 방지)
        self.throttle_scope = "verify" if self.action == "verify" else None
        return super().get_throttles()

    @extend_schema(request=PetVerifySerializer, responses={200: PetSerializer})
    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        pet = self.get_object()  # IsOwnerOrReadOnly → 본인 반려동물만
        user = request.user
        if not user.is_identity_verified:
            return Response({"detail": "본인인증을 먼저 완료해 주세요."}, status=403)
        if pet.verification_status == Pet.Verification.APPROVED:
            return Response({"detail": "이미 인증된 반려동물입니다."}, status=409)

        serializer = PetVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reg_no = serializer.validated_data["registration_number"]

        if Pet.objects.filter(
            registration_number=reg_no, verification_status=Pet.Verification.APPROVED
        ).exclude(pk=pet.pk).exists():
            return Response({"detail": "이미 다른 계정에 인증된 등록번호입니다."}, status=409)

        result = get_pet_registry().lookup(reg_no, user.legal_name, user.birth_date)
        pet.registration_number = reg_no
        if not result.found:
            # 미등록·조회 불가 → 사진·접종 기록으로 운영자 검토 (업로드는 다음 단계에서 추가)
            pet.verification_status = Pet.Verification.PENDING
        elif result.owner_matched:
            pet.verification_status = Pet.Verification.APPROVED
            pet.verified_at = timezone.now()
            pet.breed = pet.breed or result.breed
            pet.sex = pet.sex or result.sex
            if pet.neutered is None:
                pet.neutered = result.neutered
        else:
            pet.verification_status = Pet.Verification.REJECTED
        pet.save()
        return Response(PetSerializer(pet).data)
