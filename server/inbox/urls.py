from rest_framework.routers import SimpleRouter

from .views import MessageViewSet

router = SimpleRouter(trailing_slash=False)
router.register("messages", MessageViewSet, basename="message")

urlpatterns = router.urls
