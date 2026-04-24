"""ASGI config wiring HTTP + WebSocket via Channels ProtocolTypeRouter."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

# Setup Django before importing anything that touches models / apps.
import django  # noqa: E402
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from main.apps.ran.routing import websocket_urlpatterns  # noqa: E402


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(URLRouter(websocket_urlpatterns)),
})
