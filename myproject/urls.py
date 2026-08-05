from django.contrib import admin
from django.urls import include, path
from .health import health, live, ready

urlpatterns = [
    path("health/", health, name="health"),
    path("health/live/", live, name="health-live"),
    path("health/ready/", ready, name="health-ready"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("manyumbu10.urls")),
]
