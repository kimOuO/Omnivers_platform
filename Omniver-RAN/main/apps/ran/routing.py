"""Channels routing — WebSocket URL patterns for the `ran` app.

Follows backend_rule.md §7-1 URL format: /api/{version}/{System}/{Module}/{Element}
"""
from django.urls import re_path

from main.apps.ran.consumers import UELiveConsumer


websocket_urlpatterns = [
    re_path(r"^api/v0\.1/RAN/UE/live$", UELiveConsumer.as_asgi(), name="ue_live"),
]
