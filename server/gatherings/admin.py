from django.contrib import admin

from .models import Gathering, Participation


class ParticipationInline(admin.TabularInline):
    model = Participation
    extra = 0


@admin.register(Gathering)
class GatheringAdmin(admin.ModelAdmin):
    list_display = ["id", "kind", "title", "host", "region_name", "starts_at", "status", "is_hidden"]
    list_filter = ["kind", "status", "is_hidden"]
    search_fields = ["title", "content", "host__nickname", "place_name"]
    list_editable = ["is_hidden"]
    inlines = [ParticipationInline]
