"""
Root URL configuration.

API is versioned under /api/v1/ — adding /api/v2/ in the future
only requires adding a new include() here.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

    # OpenAPI 3 Schema & Interactive Swagger Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-docs"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # API v1
    path("api/v1/auth/", include("authentication.urls", namespace="authentication")),
    path("api/v1/users/", include("users.urls", namespace="users")),
    path("api/v1/profiles/", include("profiles.urls", namespace="profiles")),
    path("api/v1/projects/", include("projects.urls", namespace="projects")),
    path("api/v1/notifications/", include("notifications.urls", namespace="notifications")),
]

# Serve media files in development only.
# In production, this is handled by a web server (Nginx) or cloud storage (S3).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
