from django.contrib import admin

from .models import Pet


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "species", "size", "user", "verification_status", "created_at"]
    list_filter = ["verification_status", "species", "size"]
    search_fields = ["name", "user__nickname"]
    # 운영자 검토 대기 목록: verification_status = pending 필터로 확인
