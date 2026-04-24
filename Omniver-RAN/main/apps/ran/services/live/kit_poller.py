"""Background task that subscribes to Kit's WS stream and re-broadcasts to the `ue_live` group.

Flow:
  Kit (mitlab.ran.api ws_server on :8081)
    ──ws push──►  this client  ──group_send──►  Django Channels `ue_live`  ──►  browsers

The name is historical; what was an HTTP poller is now a WS client. On disconnect
we retry with exponential backoff so a Kit restart doesn't leave browsers stuck.

Every SAMPLE_EVERY_N_TICKS message we persist UE positions to `position_history`.

Lazy-started by the first WebSocket connection (see UELiveConsumer.connect).
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import websockets
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from django.conf import settings

from main.utils.logger import get_logger

log = get_logger(__name__)

GROUP = "ue_live"
SAMPLE_EVERY_N_TICKS = 2       # ~1s persist cadence at Kit's 2Hz push
RECONNECT_MIN_SEC = 1.0
RECONNECT_MAX_SEC = 10.0

_lock = asyncio.Lock()
_started = False


@sync_to_async
def _persist_positions(ues: list[dict]) -> int:
    """Bulk-insert UE positions to position_history. Returns row count."""
    from main.apps.ran.models import PositionHistory

    rows = []
    for ue in ues:
        name = ue.get("name")
        pos = ue.get("position") or {}
        if not name:
            continue
        rows.append(
            PositionHistory(
                entity_name=name,
                entity_type="ue",
                x=float(pos.get("x", 0) or 0),
                y=float(pos.get("y", 0) or 0),
                z=float(pos.get("z", 0) or 0),
            )
        )
    if rows:
        PositionHistory.objects.bulk_create(rows)
    return len(rows)


def _kit_ws_url() -> str:
    # Settings key mirrors HTTP_KIT_* for symmetry; can be overridden in compose.
    host = getattr(settings, "KIT_HOST", "localhost")
    port = getattr(settings, "KIT_WS_PORT", "8081")
    return f"ws://{host}:{port}"


async def _forward_loop() -> None:
    """Connect to Kit's WS, forward snapshots, reconnect with backoff on drop."""
    layer = get_channel_layer()
    url = _kit_ws_url()
    log.info("[ue_live] kit ws client starting — url=%s", url)

    tick = 0
    backoff = RECONNECT_MIN_SEC

    while True:
        try:
            async with websockets.connect(url, open_timeout=5, ping_interval=20) as ws:
                log.info("[ue_live] connected to Kit WS")
                backoff = RECONNECT_MIN_SEC  # reset on success
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:  # noqa: BLE001
                        continue
                    ues = msg.get("ues") if isinstance(msg, dict) else None
                    if not isinstance(ues, list):
                        ues = []

                    await layer.group_send(
                        GROUP,
                        {
                            "type": "live.snapshot",
                            "payload": {
                                "type": "ue_update",
                                "ts": msg.get("ts", time.time()),
                                "ues": ues,
                            },
                        },
                    )

                    tick += 1
                    if ues and tick % SAMPLE_EVERY_N_TICKS == 0:
                        try:
                            await _persist_positions(ues)
                        except Exception as e:  # noqa: BLE001
                            log.warning("[ue_live] persist failed: %s", e)
        except Exception as e:  # noqa: BLE001
            log.warning("[ue_live] kit ws disconnected (%s) — retry in %.1fs", e, backoff)

        # Always broadcast an empty snapshot so the frontend knows nothing is live yet.
        await layer.group_send(
            GROUP,
            {
                "type": "live.snapshot",
                "payload": {"type": "ue_update", "ts": time.time(), "ues": []},
            },
        )
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, RECONNECT_MAX_SEC)


async def ensure_started() -> None:
    """Idempotent launcher — multiple WS clients all call this on connect."""
    global _started
    async with _lock:
        if _started:
            return
        asyncio.create_task(_forward_loop())
        _started = True
        log.info("[ue_live] forward task scheduled")
