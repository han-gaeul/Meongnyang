from django.urls import path

from . import views

urlpatterns = [
    path("meetups/token", views.MeetupTokenView.as_view(), name="meetup-token"),
    path("meetups/confirm", views.MeetupConfirmView.as_view(), name="meetup-confirm"),
    path("neighbors", views.NeighborListView.as_view(), name="neighbors"),
]
