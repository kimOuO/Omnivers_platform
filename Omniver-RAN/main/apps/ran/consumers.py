"""WebSocket consumers — real-time push channel (ASGI side).

Per backend_rule.md, REST APIs stay POST-only (§7-2). WebSocket is a separate
transport layer used for read-side real-time streaming; command issuance still
flows through the REST Actors.
"""
from __future__ import annotations

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from main.apps.ran.services.live.kit_poller import GROUP, ensure_started
from main.utils.logger import get_logger

log = get_logger(__name__)


class UELiveConsumer(AsyncJsonWebsocketConsumer):
    """Subscribes a client to the `ue_live` group.

    URL: /api/v0.1/RAN/UE/live
    First message to client: {"type": "hello", "group": "ue_live"}
    Then every POLL_INTERVAL_SEC the client receives:
        {"type": "ue_update", "ts": <epoch>, "ues": [ {name, position, rsrp_dbm, ...}, ... ]}
    """

    async def connect(self) -> None:
        await self.channel_layer.group_add(GROUP, self.channel_name)
        await self.accept()
        await self.send_json({"type": "hello", "group": GROUP})
        await ensure_started()
        log.info("[ue_live] client connected channel=%s", self.channel_name)

    async def disconnect(self, code: int) -> None:
        await self.channel_layer.group_discard(GROUP, self.channel_name)
        log.info("[ue_live] client disconnected code=%s channel=%s", code, self.channel_name)

    async def live_snapshot(self, event: dict) -> None:
        """Consumer handler for group_send(type='live.snapshot', ...)."""
        await self.send_json(event["payload"])
