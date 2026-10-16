from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.db import connection
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def healthz(request):
    """로드밸런서·컨테이너 헬스체크: DB까지 확인"""
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
    except Exception:  # noqa: BLE001
        return JsonResponse({"ok": False}, status=503)
    return JsonResponse({"ok": True})


urlpatterns = [
    path("healthz", healthz),
    path("admin/", admin.site.urls),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("pets.urls")),
    path("api/v1/", include("uploads.urls")),
    path("api/v1/", include("community.urls")),
    path("api/v1/", include("gatherings.urls")),
    path("api/v1/", include("meetups.urls")),
    path("api/v1/", include("favors.urls")),
    path("api/v1/", include("places.urls")),
    path("api/v1/", include("notifications.urls")),
    path("api/v1/", include("inbox.urls")),
    path("api/v1/", include("journal.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
