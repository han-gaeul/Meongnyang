from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """로그인 사용자만. 읽기는 누구나, 수정·삭제는 작성자만.

    기존 웹에서 삭제 시 작성자 확인이 빠졌던 문제를 막기 위해
    소유자가 있는 모든 ViewSet에 기본으로 붙인다.
    permission_classes를 지정하면 기본 IsAuthenticated가 사라지므로
    로그인 확인도 이 클래스 안에서 함께 한다.
    객체의 소유자 필드 이름은 뷰의 `owner_field`로 바꿀 수 있다(기본 "user").
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner_field = getattr(view, "owner_field", "user")
        return getattr(obj, f"{owner_field}_id", None) == request.user.id


class IsVerifiedMember(BasePermission):
    """본인인증 + 인증된 반려동물 1마리 이상. 커뮤니티·모임·부탁 기능에 사용."""

    message = "본인인증과 반려동물 인증을 마친 회원만 이용할 수 있습니다."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_verified_member)
