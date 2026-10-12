from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.permissions import IsOwnerOrReadOnly, IsVerifiedMember
from common.visibility import visible_to
from moderation.serializers import ReportCreateSerializer, ReportResultSerializer
from moderation.services import report_content

from .models import Comment, Post, PostImage
from .serializers import CommentSerializer, PostSerializer

# 읽기는 로그인만 하면 가능(인증 전 둘러보기), 쓰기·반응은 인증 회원만.
WRITE_ACTIONS = {"create", "like", "unlike", "report"}


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer

    def get_permissions(self):
        if self.action in WRITE_ACTIONS or (
            self.action == "comments" and self.request.method == "POST"
        ):
            return [IsVerifiedMember()]
        if self.action in {"update", "partial_update", "destroy"}:
            return [IsOwnerOrReadOnly()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # OpenAPI 스키마 생성 시
            return Post.objects.none()
        user = self.request.user
        visible_comments = visible_to(Comment.objects.all(), user)
        qs = (
            visible_to(Post.objects.all(), user)
            .select_related("user")
            .prefetch_related(
                "tags", Prefetch("post_images", queryset=PostImage.objects.select_related("image"))
            )
            .annotate(
                like_count=Count("like_users", distinct=True),
                comment_count=Count(
                    "comments", filter=Q(comments__in=visible_comments), distinct=True
                ),
                is_liked=Exists(Post.like_users.through.objects.filter(post=OuterRef("pk"), user=user)),
            )
        )
        if self.action != "list":
            return qs

        params = self.request.query_params
        if species := params.get("species"):
            if species in (Post.Species.DOG, Post.Species.CAT):
                qs = qs.filter(species__in=[species, Post.Species.ALL])
        if tag := params.get("tag"):
            qs = qs.filter(tags__name=tag.lstrip("#"))
        if q := params.get("q", "").strip():
            qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))
        if author := params.get("author"):
            qs = qs.filter(user_id=author)
        if region := params.get("region"):
            qs = qs.filter(region_name=region)
        return qs

    @extend_schema(
        parameters=[
            OpenApiParameter("species", str, enum=["dog", "cat"], description="해당 종 + '모두' 글"),
            OpenApiParameter("tag", str),
            OpenApiParameter("q", str, description="제목·내용 검색"),
            OpenApiParameter("author", int),
            OpenApiParameter("region", str, description="동네 이름"),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user, region_name=user.region_name)

    def _refreshed(self, pk):
        return self.get_queryset().get(pk=pk)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        post = self._refreshed(serializer.instance.pk)
        return Response(self.get_serializer(post).data, status=201)

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(self.get_serializer(self._refreshed(kwargs["pk"])).data)

    @extend_schema(request=None, responses={200: PostSerializer})
    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        post = self.get_object()
        post.like_users.add(request.user)
        return Response(self.get_serializer(self._refreshed(post.pk)).data)

    @extend_schema(request=None, responses={200: PostSerializer})
    @like.mapping.delete
    def unlike(self, request, pk=None):
        post = self.get_object()
        post.like_users.remove(request.user)
        return Response(self.get_serializer(self._refreshed(post.pk)).data)

    @extend_schema(request=ReportCreateSerializer, responses={200: ReportResultSerializer})
    @action(detail=True, methods=["post"])
    def report(self, request, pk=None):
        post = self.get_object()
        if post.user_id == request.user.id:
            return Response({"detail": "내 글은 신고할 수 없습니다."}, status=400)
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = report_content(post, request.user, **serializer.validated_data)
        return Response({"created": result.created, "hidden": result.hidden})

    @extend_schema(methods=["GET"], responses={200: CommentSerializer(many=True)})
    @extend_schema(methods=["POST"], request=CommentSerializer, responses={201: CommentSerializer})
    @action(detail=True, methods=["get", "post"], pagination_class=None)
    def comments(self, request, pk=None):
        post = self.get_object()
        if request.method == "POST":
            serializer = CommentSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save(post=post, user=request.user)
            return Response(serializer.data, status=201)
        comments = visible_to(post.comments.select_related("user"), request.user)
        return Response(CommentSerializer(comments, many=True, context={"request": request}).data)


class CommentViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """댓글 삭제(작성자만)와 신고(인증 회원)."""

    serializer_class = CommentSerializer

    def get_permissions(self):
        if self.action == "report":
            return [IsVerifiedMember()]
        return [IsOwnerOrReadOnly()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Comment.objects.none()
        return visible_to(Comment.objects.select_related("user"), self.request.user)

    @extend_schema(request=ReportCreateSerializer, responses={200: ReportResultSerializer})
    @action(detail=True, methods=["post"])
    def report(self, request, pk=None):
        comment = self.get_object()
        if comment.user_id == request.user.id:
            return Response({"detail": "내 댓글은 신고할 수 없습니다."}, status=400)
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = report_content(comment, request.user, **serializer.validated_data)
        return Response({"created": result.created, "hidden": result.hidden})
