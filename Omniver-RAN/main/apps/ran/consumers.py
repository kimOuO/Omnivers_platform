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


class IngestConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket server at /api/v0.1/RAN/Ingest/ws/

    Receives WS connections from RAN-sim and processes signal ingest payloads:
    {
      "ts": "2024-...",
      "session_uuid": "...",
      "signals": [
        {"ue_name": "...", "serving_gnb": "...", "serving_pci": 100,
         "serving_cell_id": "...", "rsrp_dbm": ..., "sinr_db": ...,
         "rsrp_map": {...}, "position": [x, y, z]},
        ...
      ]
    }
    """

    async def connect(self) -> None:
        await self.accept()
        log.info("[ingest_ws] WS connection accepted")

    async def disconnect(self, code: int) -> None:
        log.info("[ingest_ws] WS disconnected code=%s", code)

    async def receive_json(self, content: dict) -> None:
        """Receive and process ingest payload from RAN-sim."""
        from main.apps.ran.serializers.ingest_serializers import SignalBatchWriteSerializer
        from main.apps.ran.services.business.ingest_operations import IngestBusinessService
        from asgiref.sync import sync_to_async

        try:
            ser = SignalBatchWriteSerializer(data=content)
            if not ser.is_valid():
                log.warning("[ingest_ws] validation failed: %s", ser.errors)
                await self.send_json({"error": ser.errors})
                return

            data = ser.validated_data
            result = await sync_to_async(IngestBusinessService.ingest_signals)(
                data["signals"], ts=data.get("ts"), session_uuid=data.get("session_uuid")
            )
            await self.send_json({"accepted": result["accepted"], "kit_errors": result["kit_errors"]})
        except Exception as e:  # noqa: BLE001
            log.exception("[ingest_ws] error processing payload")
            await self.send_json({"error": str(e)})
