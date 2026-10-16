import secrets

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .identity import get_identity_provider, hash_ci
from .models import IdentityVerification, SocialAccount
from .serializers import (
    AuthConfigSerializer,
    check_invite,
    IdentityVerifySerializer,
    LogoutSerializer,
    MeSerializer,
    PublicUserSerializer,
    SignupSerializer,
    SocialLoginSerializer,
    TokenPairSerializer,
)
from .social import VERIFIERS, SocialAuthError

User = get_user_model()


def issue_tokens(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class SignupView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = SignupSerializer
    throttle_scope = "auth"

    @extend_schema(responses={201: TokenPairSerializer})
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(issue_tokens(user), status=status.HTTP_201_CREATED)


def _unique_nickname(preferred: str | None) -> str:
    base = (preferred or "이웃")[:14]
    if not User.objects.filter(nickname=base).exists():
        return base
    while True:
        candidate = f"{base}{secrets.randbelow(10000):04d}"
        if not User.objects.filter(nickname=candidate).exists():
            return candidate


class SocialLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(request=SocialLoginSerializer, responses={200: TokenPairSerializer})
    def post(self, request, provider: str):
        verifier = VERIFIERS.get(provider)
        if verifier is None:
            return Response({"detail": "지원하지 않는 로그인 방식입니다."}, status=404)
        serializer = SocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            profile = verifier(serializer.validated_data["token"])
        except SocialAuthError as exc:
            return Response({"detail": "소셜 로그인 검증에 실패했습니다.", "code": str(exc)}, status=401)

        account = SocialAccount.objects.select_related("user").filter(
            provider=provider, provider_uid=profile.uid
        ).first()
        created = account is None
        if created:
            check_invite(serializer.validated_data.get("invite_code"))
            with transaction.atomic():
                email = profile.email
                if email and User.objects.filter(email__iexact=email).exists():
                    # 같은 이메일의 기존 계정에 자동 연결하지 않는다(계정 탈취 방지).
                    email = None
                user = User.objects.create_user(
                    email=email, password=None, nickname=_unique_nickname(profile.nickname)
                )
                SocialAccount.objects.create(user=user, provider=provider, provider_uid=profile.uid)
        else:
            user = account.user
        if not user.is_active:
            return Response({"detail": "비활성화된 계정입니다."}, status=403)
        return Response({**issue_tokens(user), "created": created})


class LogoutView(APIView):
    @extend_schema(request=LogoutSerializer, responses={205: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            if token["user_id"] != str(request.user.id) and token["user_id"] != request.user.id:
                return Response(status=403)
            token.blacklist()
        except TokenError:
            return Response({"detail": "유효하지 않은 토큰입니다."}, status=400)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class IdentityVerifyView(APIView):
    """휴대폰 본인인증 결과 확인. 로그인한 본인 계정에만 적용된다."""

    throttle_scope = "verify"

    @extend_schema(request=IdentityVerifySerializer, responses={200: MeSerializer})
    def post(self, request):
        serializer = IdentityVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tx_id = serializer.validated_data["transaction_id"]
        user = request.user

        if user.is_identity_verified:
            return Response({"detail": "이미 본인인증을 마쳤습니다."}, status=409)
        if IdentityVerification.objects.filter(transaction_id=tx_id).exists():
            return Response({"detail": "이미 사용된 인증 요청입니다."}, status=409)

        provider = get_identity_provider()
        result = provider.verify(tx_id)
        IdentityVerification.objects.create(
            user=user,
            provider=provider.name,
            transaction_id=tx_id,
            succeeded=result.verified,
            failure_reason=result.failure_reason,
        )
        if not result.verified:
            return Response({"detail": "본인인증에 실패했습니다."}, status=400)

        ci_hash = hash_ci(result.ci)
        duplicate = Response({"detail": "이미 다른 계정에서 본인인증된 사용자입니다."}, status=409)
        # 같은 사람(CI)이 이미 다른 계정으로 인증함 → 1인 1계정
        if User.objects.filter(ci_hash=ci_hash).exclude(pk=user.pk).exists():
            return duplicate

        user.is_identity_verified = True
        user.ci_hash = ci_hash
        user.legal_name = result.name
        user.birth_date = result.birth_date
        try:
            with transaction.atomic():
                user.save(update_fields=["is_identity_verified", "ci_hash", "legal_name", "birth_date"])
        except IntegrityError:  # 동시 요청 경합
            user.refresh_from_db()
            return duplicate
        return Response(MeSerializer(user).data)


class MeView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class UserDetailView(generics.RetrieveAPIView):
    serializer_class = PublicUserSerializer
    queryset = User.objects.filter(is_active=True)


class FollowView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk, is_active=True)
        if target == request.user:
            return Response({"detail": "자기 자신은 팔로우할 수 없습니다."}, status=400)
        request.user.followings.add(target)
        return Response(status=204)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        request.user.followings.remove(get_object_or_404(User, pk=pk))
        return Response(status=204)


class BlockView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk, is_active=True)
        if target == request.user:
            return Response({"detail": "자기 자신은 차단할 수 없습니다."}, status=400)
        request.user.blocks.add(target)
        request.user.followings.remove(target)
        return Response(status=204)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        request.user.blocks.remove(get_object_or_404(User, pk=pk))
        return Response(status=204)


class AuthConfigView(APIView):
    """가입 화면용: 초대 코드가 필요한지, 베타 운영 중인지"""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: AuthConfigSerializer})
    def get(self, request):
        from django.conf import settings

        return Response({
            "invite_required": settings.INVITE_REQUIRED,
            "beta": "mock" in (settings.IDENTITY_PROVIDER, settings.PET_REGISTRY_PROVIDER),
        })
