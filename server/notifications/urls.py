from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import DeviceView, NotificationViewSet, UnreadView

router = SimpleRouter(trailing_slash=False)
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("notifications/unread", UnreadView.as_view(), name="unread"),
    path("devices", DeviceView.as_view(), name="devices"),
    *router.urls,
]
