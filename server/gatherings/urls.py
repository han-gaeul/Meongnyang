from rest_framework.routers import SimpleRouter

from .views import GatheringViewSet

router = SimpleRouter(trailing_slash=False)
router.register("gatherings", GatheringViewSet, basename="gathering")

urlpatterns = router.urls
