"""Base Django settings shared across environments."""
from __future__ import annotations

from pathlib import Path

from main.utils.env_loader import get_bool, get_list, get_str

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = get_str("DJANGO_SECRET_KEY", "insecure-default-override-me")
DEBUG = get_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = get_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    # daphne must be first — it hijacks `runserver` for ASGI/WebSocket support.
    "daphne",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "channels",
    "corsheaders",
    "main.apps.ran.apps.RanConfig",
]

# WebSocket fan-out (backend_rule.md §7-2 POST-only limit scopes REST APIs;
# WebSocket is a separate transport used for read-side real-time push).
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "main.urls"

TEMPLATES: list[dict] = []

WSGI_APPLICATION = "main.wsgi.application"
ASGI_APPLICATION = "main.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": get_str("DB_HOST", "localhost"),
        "PORT": get_str("DB_PORT", "5432"),
        "NAME": get_str("DB_NAME", "ran_dt"),
        "USER": get_str("DB_USER", "ran"),
        "PASSWORD": get_str("DB_PASSWORD", "ran"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS — per backend_rule.md §10-3
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True

TIME_ZONE = "UTC"
USE_TZ = True

STATIC_URL = "/static/"

# Cross-module API targets
KIT_HOST = get_str("HTTP_KIT_HOST", "localhost")
KIT_PORT = get_str("HTTP_KIT_PORT", "8080")
KIT_WS_PORT = get_str("WS_KIT_PORT", "8081")
KIT_BASE_URL = f"http://{KIT_HOST}:{KIT_PORT}"
