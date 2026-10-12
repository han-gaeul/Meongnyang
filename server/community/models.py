from django.conf import settings
from django.db import models

from common.models import Moderated


class Tag(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class Post(Moderated):
    class Species(models.TextChoices):
        ALL = "all", "모두"
        DOG = "dog", "강아지"
        CAT = "cat", "고양이"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    # 작성 당시 작성자의 동네. 동네별 피드에 사용.
    region_name = models.CharField(max_length=50, blank=True, db_index=True)
    species = models.CharField(max_length=3, choices=Species.choices, default=Species.ALL)
    title = models.CharField(max_length=50)
    content = models.TextField(max_length=3000)
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)
    like_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="liked_posts", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.title


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="post_images")
    image = models.OneToOneField("uploads.UploadedImage", on_delete=models.CASCADE, related_name="post_image")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class Comment(Moderated):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_comments")
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
