from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["id", "content_type", "object_id", "reason", "reporter", "resolved", "created_at"]
    list_filter = ["resolved", "reason", "content_type"]
    search_fields = ["detail", "reporter__nickname"]
    actions = ["mark_resolved"]

    @admin.action(description="검토 완료로 표시")
    def mark_resolved(self, request, queryset):
        queryset.update(resolved=True)
