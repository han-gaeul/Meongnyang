from django.contrib import admin

from .models import Comment, Post, Tag


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "user", "region_name", "species", "is_hidden", "created_at"]
    list_filter = ["is_hidden", "species"]
    search_fields = ["title", "content", "user__nickname"]
    list_editable = ["is_hidden"]  # 신고로 숨겨진 글 복구·운영자 숨김


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["id", "post", "user", "content", "is_hidden", "created_at"]
    list_filter = ["is_hidden"]
    list_editable = ["is_hidden"]


admin.site.register(Tag)
