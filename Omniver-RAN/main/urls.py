from django.urls import include, path

urlpatterns = [
    path("api/v0.1/", include("main.apps.ran.api.urls")),
]
