from django.contrib import admin
from django.utils import timezone

from .models import Place, PlaceReview, ReviewImage


class ReviewInline(admin.TabularInline):
    model = PlaceReview
    extra = 0
    fields = ["user", "pet_size", "pet_weight_kg", "visited_on", "admitted", "space", "floor_ok", "verified_visit", "is_hidden"]
    readonly_fields = ["user", "pet_size", "pet_weight_kg", "visited_on", "verified_visit"]


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "category", "region_name", "status", "source", "is_24h", "policy_checked_at"]
    list_filter = ["status", "category", "source", "is_24h"]
    search_fields = ["name", "address", "region_name"]
    inlines = [ReviewInline]
    actions = ["approve", "mark_policy_checked", "close"]

    @admin.action(description="게시 (제보 승인)")
    def approve(self, request, queryset):
        queryset.update(status=Place.Status.APPROVED)

    @admin.action(description="동반 조건 확인함 (오늘 날짜로)")
    def mark_policy_checked(self, request, queryset):
        queryset.update(policy_checked_at=timezone.now())

    @admin.action(description="폐업·비공개")
    def close(self, request, queryset):
        queryset.update(status=Place.Status.CLOSED)


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0


@admin.register(PlaceReview)
class PlaceReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "place", "user", "pet_size", "pet_weight_kg", "admitted", "verified_visit", "is_hidden"]
    list_filter = ["admitted", "verified_visit", "is_hidden", "pet_size"]
    list_editable = ["is_hidden"]
    inlines = [ReviewImageInline]
