from django.db import transaction
from rest_framework import serializers

from uploads.models import UploadedImage
from uploads.serializers import ImageSerializer

from .models import Comment, Post, PostImage, Tag

MAX_IMAGES = 5
MAX_TAGS = 5


class TagListField(serializers.ListField):
    """쓰기: 문자열 목록 / 읽기: Tag 관계 → 이름 목록."""

    child = serializers.CharField(max_length=20)

    def to_representation(self, data):
        if hasattr(data, "all"):
            return [t.name for t in data.all()]
        return super().to_representation(data)


class AuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nickname = serializers.CharField()


class PostSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(source="user", read_only=True)
    images = serializers.SerializerMethodField()
    tags = TagListField(required=False, max_length=MAX_TAGS)
    image_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True, max_length=MAX_IMAGES
    )
    like_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "region_name",
            "species",
            "title",
            "content",
            "tags",
            "images",
            "image_ids",
            "like_count",
            "comment_count",
            "is_liked",
            "is_mine",
            "is_hidden",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "region_name", "is_hidden", "created_at", "updated_at"]

    def get_images(self, obj) -> list[dict]:
        return ImageSerializer(
            [pi.image for pi in obj.post_images.all()], many=True, context=self.context
        ).data

    def get_is_mine(self, obj) -> bool:
        request = self.context.get("request")
        return bool(request and obj.user_id == request.user.id)

    def validate_tags(self, value):
        cleaned = []
        for raw in value:
            name = raw.strip().lstrip("#")
            if name and name not in cleaned:
                cleaned.append(name)
        return cleaned

    def validate_image_ids(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError("같은 사진을 두 번 넣을 수 없습니다.")
        request = self.context["request"]
        images = {
            img.id: img
            for img in UploadedImage.objects.filter(id__in=value, owner=request.user).select_related(
                "post_image"
            )
        }
        for image_id in value:
            img = images.get(image_id)
            if img is None:
                raise serializers.ValidationError("올리지 않았거나 다른 사람의 사진입니다.")
            attached = getattr(img, "post_image", None)
            if attached and (self.instance is None or attached.post_id != self.instance.id):
                raise serializers.ValidationError("이미 다른 글에 사용된 사진입니다.")
        return [images[i] for i in value]

    def _set_tags(self, post, names):
        tags = [Tag.objects.get_or_create(name=n)[0] for n in names]
        post.tags.set(tags)

    def _set_images(self, post, images):
        PostImage.objects.filter(post=post).exclude(image__in=images).delete()
        for order, img in enumerate(images):
            PostImage.objects.update_or_create(image=img, defaults={"post": post, "order": order})

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        images = validated_data.pop("image_ids", [])
        post = Post.objects.create(**validated_data)
        self._set_tags(post, tags)
        self._set_images(post, images)
        return post

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        images = validated_data.pop("image_ids", None)
        instance = super().update(instance, validated_data)
        if tags is not None:
            self._set_tags(instance, tags)
        if images is not None:
            self._set_images(instance, images)
        return instance


class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(source="user", read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "post", "author", "content", "is_mine", "is_hidden", "created_at"]
        read_only_fields = ["id", "post", "is_hidden", "created_at"]

    def get_is_mine(self, obj) -> bool:
        request = self.context.get("request")
        return bool(request and obj.user_id == request.user.id)
