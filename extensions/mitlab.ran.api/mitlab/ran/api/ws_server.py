"""WebSocket server — pushes UE snapshots to subscribed clients.

Runs on Kit's asyncio loop (main thread), so USD access is safe without locks.
Reuses `_scan_stage()` from extension.py so the WS payload matches GET /ues.

Wire format per push:
  { "type": "ue_update", "ts": <unix-seconds>, "ues": [<UE>, ...] }
"""
from __future__ import annotations

import asyncio
import json
import time

import omni.usd
import websockets

WS_PORT = 8081
PUSH_INTERVAL_SEC = 0.5  # 2 Hz


def _build_snapshot(ext) -> dict:
    # Local import to break the circular reference (extension imports ws_server).
    from .extension import _scan_stage
    stage = omni.usd.get_context().get_stage()
    builder = ext._get_scene_builder()
    _, ues = _scan_stage(stage, builder)
    return {"type": "ue_update", "ts": time.time(), "ues": ues}


async def _handler(ws, ext) -> None:
    """Per-connection push loop. Drop the client on any send error."""
    ext._ws_clients.add(ws)
    print(f"[RAN WS] client connected; now {len(ext._ws_clients)}")
    try:
        while True:
            try:
                payload = _build_snapshot(ext)
            except Exception as e:  # noqa: BLE001
                # USD access can transiently fail during stage swap; skip this tick.
                print(f"[RAN WS] snapshot error: {e}")
                payload = {"type": "ue_update", "ts": time.time(), "ues": []}
            await ws.send(json.dumps(payload))
            await asyncio.sleep(PUSH_INTERVAL_SEC)
    except websockets.ConnectionClosed:
        pass
    except Exception as e:  # noqa: BLE001
        print(f"[RAN WS] handler error: {e}")
    finally:
        ext._ws_clients.discard(ws)
        print(f"[RAN WS] client disconnected; now {len(ext._ws_clients)}")


async def serve(ext) -> None:
    """Long-running task — schedule via `omni.kit.async_engine.run_coroutine(serve(ext))`."""
    ext._ws_clients = set()
    try:
        server = await websockets.serve(
            lambda ws: _handler(ws, ext),
            host="0.0.0.0",
            port=WS_PORT,
            ping_interval=20,
            ping_timeout=20,
        )
    except OSError as e:
        print(f"[RAN WS] failed to bind :{WS_PORT} — {e}")
        return
    ext._ws_server = server
    print(f"[RAN WS] server listening on :{WS_PORT}")
    try:
        await server.wait_closed()
    except asyncio.CancelledError:
        pass
