from django.urls import path

from .views import ImageUploadView

urlpatterns = [path("uploads/images", ImageUploadView.as_view(), name="image-upload")]
