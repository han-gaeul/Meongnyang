from rest_framework.routers import SimpleRouter

from .views import PetViewSet

router = SimpleRouter(trailing_slash=False)
router.register("pets", PetViewSet, basename="pet")

urlpatterns = router.urls
