from rest_framework.routers import SimpleRouter

from .views import CommentViewSet, PostViewSet

router = SimpleRouter(trailing_slash=False)
router.register("posts", PostViewSet, basename="post")
router.register("comments", CommentViewSet, basename="comment")

urlpatterns = router.urls
