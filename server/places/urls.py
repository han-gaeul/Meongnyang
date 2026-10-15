from rest_framework.routers import SimpleRouter

from .views import PlaceViewSet, ReviewViewSet

router = SimpleRouter(trailing_slash=False)
router.register("places", PlaceViewSet, basename="place")
router.register("place-reviews", ReviewViewSet, basename="place-review")

urlpatterns = router.urls
