from django.contrib import admin

from .models import JournalEntry


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    """운영 확인용. 경로(route)는 개인정보라 목록에 띄우지 않는다."""

    list_display = ["id", "pet", "kind", "date", "user", "created_at"]
    list_filter = ["kind"]
    exclude = ["route"]
