from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import CareSheetDraftView, FavorViewSet

router = SimpleRouter(trailing_slash=False)
router.register("favors", FavorViewSet, basename="favor")

urlpatterns = [
    path("pets/<int:pk>/care-sheet", CareSheetDraftView.as_view(), name="pet-care-sheet"),
    *router.urls,
]
