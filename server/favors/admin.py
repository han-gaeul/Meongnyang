from django.contrib import admin

from .models import Favor, FavorApplication, FavorThanks


class FavorApplicationInline(admin.TabularInline):
    model = FavorApplication
    extra = 0


class FavorThanksInline(admin.StackedInline):
    model = FavorThanks
    extra = 0


@admin.register(Favor)
class FavorAdmin(admin.ModelAdmin):
    list_display = ["id", "kind", "title", "requester", "helper", "visit_home", "starts_at", "status", "is_hidden"]
    list_filter = ["kind", "status", "visit_home", "is_hidden"]
    search_fields = ["title", "content", "requester__nickname", "helper__nickname"]
    list_editable = ["is_hidden"]
    inlines = [FavorApplicationInline, FavorThanksInline]
