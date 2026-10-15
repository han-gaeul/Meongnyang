from rest_framework.routers import SimpleRouter

from .views import JournalViewSet

router = SimpleRouter(trailing_slash=False)
router.register("journal", JournalViewSet, basename="journal")

urlpatterns = router.urls
