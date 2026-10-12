from django.contrib import admin

from .models import Meetup


@admin.register(Meetup)
class MeetupAdmin(admin.ModelAdmin):
    list_display = ["id", "user_a", "user_b", "met_on", "distance_m", "gathering"]
    list_filter = ["met_on"]
    search_fields = ["user_a__nickname", "user_b__nickname"]
