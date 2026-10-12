from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import IdentityVerification, SocialAccount, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["id", "nickname", "email", "is_identity_verified", "date_joined"]
    search_fields = ["nickname", "email"]
    fieldsets = (
        (None, {"fields": ("email", "nickname", "password")}),
        ("동네", {"fields": ("region_name", "latitude", "longitude")}),
        ("본인인증", {"fields": ("is_identity_verified",)}),
        ("권한", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = ((None, {"fields": ("email", "nickname", "password1", "password2")}),)


admin.site.register(SocialAccount)
admin.site.register(IdentityVerification)
