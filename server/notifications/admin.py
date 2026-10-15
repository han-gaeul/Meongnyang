from django.contrib import admin

from .models import DeviceToken, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "kind", "title", "read_at", "created_at"]
    list_filter = ["kind"]
    search_fields = ["user__nickname", "title"]


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "platform", "active", "updated_at"]
    list_filter = ["platform", "active"]
