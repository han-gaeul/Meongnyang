from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """신고된 쪽지 확인용. 평소에는 열람하지 않는다."""

    list_display = ["id", "sender", "recipient", "created_at", "read_at"]
    search_fields = ["sender__nickname", "recipient__nickname"]
