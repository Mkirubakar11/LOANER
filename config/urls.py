"""
URL configuration for LOANER project.
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

    # Django Admin
    path(
        "admin/",
        admin.site.urls,
    ),

    # LOANER API
    path(
        "api/accounts/",
        include("accounts.urls"),
    ),

    # OpenAPI Schema
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),

    # Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema"
        ),
        name="swagger-ui",
    ),

    # ReDoc Documentation
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(
            url_name="schema"
        ),
        name="redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)