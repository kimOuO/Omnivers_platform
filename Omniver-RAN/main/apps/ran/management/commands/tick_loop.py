"""Tick loop — 每 interval_ms 做一次模擬節拍。

取代原本 `dt-ueinference LoopController` 的角色。流程：
  1. 讀最新 SceneSnapshot 的 scene_id
  2. KitBusinessService.list_ues() 拉 UE 位置
  3. POST ranp-sim ComputeRunner/compute
  4. in-process 呼叫 IngestBusinessService.ingest_signals（不繞 HTTP）

用法：
    python manage.py tick_loop                # 走 env TICK_INTERVAL_MS（預設 500）
    python manage.py tick_loop --interval-ms 1000
    python manage.py tick_loop --scene-id my_scene
"""
from __future__ import annotations

import signal
import time
from typing import Any

from django.core.management.base import BaseCommand

from main.apps.ran.models import SceneSnapshot
from main.apps.ran.services.business.ingest_operations import IngestBusinessService
from main.apps.ran.services.business.kit_operations import KitBusinessService
from main.apps.ran.services.business.ranpsim_operations import RanpsimBusinessService
from main.apps.ran.services.optional.translation.payload_translator import PayloadTranslator
from main.utils.env_loader import get_int, get_str
from main.utils.logger import get_logger

log = get_logger(__name__)


class Command(BaseCommand):
    help = "Periodic tick loop: Kit UE → ranp-sim compute → Omniverse signal ingest."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop = False
        self._stats = {"ticks": 0, "errors": 0, "skipped_no_ue": 0, "skipped_no_scene": 0}

    def add_arguments(self, parser):
        parser.add_argument("--interval-ms", type=int, default=None,
                            help="Tick interval in ms (default: env TICK_INTERVAL_MS=500)")
        parser.add_argument("--scene-id", type=str, default=None,
                            help="Override scene_id (default: latest SceneSnapshot)")
        parser.add_argument("--max-ticks", type=int, default=0,
                            help="Stop after N ticks (0 = run forever)")

    def handle(self, *args, **opts):
        interval_ms = opts.get("interval_ms") or get_int("TICK_INTERVAL_MS", 500)
        scene_id_override = opts.get("scene_id") or get_str("TICK_SCENE_ID", "")
        max_ticks = int(opts.get("max_ticks") or 0)

        signal.signal(signal.SIGINT, self._on_stop)
        signal.signal(signal.SIGTERM, self._on_stop)

        log.info("tick_loop: starting interval=%dms scene_id=%s max_ticks=%d",
                 interval_ms, scene_id_override or "<latest>", max_ticks)

        while not self._stop:
            t0 = time.perf_counter()
            try:
                self._run_one_tick(scene_id_override)
            except Exception as e:  # noqa: BLE001
                self._stats["errors"] += 1
                log.exception("tick_loop: tick #%d failed: %s", self._stats["ticks"], e)

            self._stats["ticks"] += 1
            if max_ticks and self._stats["ticks"] >= max_ticks:
                break

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            sleep_ms = max(0.0, interval_ms - elapsed_ms)
            if elapsed_ms > interval_ms:
                log.warning("tick_loop: tick overran interval (%.1f > %d ms)",
                            elapsed_ms, interval_ms)
            # 切小段 sleep 方便即時響應 SIGINT
            end_at = time.perf_counter() + sleep_ms / 1000.0
            while not self._stop and time.perf_counter() < end_at:
                time.sleep(min(0.05, end_at - time.perf_counter()))

        log.info("tick_loop: stopped %s", self._stats)

    def _on_stop(self, signum, frame):  # noqa: ARG002
        log.info("tick_loop: received signal %d, shutting down", signum)
        self._stop = True

    # -----------------------------------------------------------------

    def _run_one_tick(self, scene_id_override: str) -> None:
        # 1) scene_id
        if scene_id_override:
            scene_id = scene_id_override
        else:
            snap = SceneSnapshot.objects.order_by("-scene_created_at").first()
            if snap is None:
                self._stats["skipped_no_scene"] += 1
                if self._stats["skipped_no_scene"] % 20 == 1:
                    log.warning("tick_loop: no SceneSnapshot yet — skipping tick")
                return
            scene_id = snap.scene_id

        # 2) pull UEs from Kit
        try:
            kit_ues: Any = KitBusinessService.list_ues()
        except Exception as e:  # noqa: BLE001
            log.warning("tick_loop: Kit list_ues failed: %s", e)
            self._stats["errors"] += 1
            return
        ue_positions = PayloadTranslator.kit_ues_to_ranpsim_positions(kit_ues)
        if not ue_positions:
            self._stats["skipped_no_ue"] += 1
            if self._stats["skipped_no_ue"] % 20 == 1:
                log.info("tick_loop: no UE in Kit — skipping")
            return

        # 3) POST ranp-sim compute
        timestamp_ms = int(time.time() * 1000)
        compute_response = RanpsimBusinessService.compute(
            scene_id=scene_id,
            timestamp_ms=timestamp_ms,
            ue_positions=ue_positions,
        )

        # 4) ingest signals (in-process, no HTTP)
        compute_data = (
            compute_response.get("data", {}) if isinstance(compute_response, dict) else {}
        )
        signals = PayloadTranslator.ranpsim_output_to_signals(compute_data)
        if not signals:
            log.debug("tick_loop: ranp-sim returned no ue_status — no-op")
            return

        IngestBusinessService.ingest_signals(signals)
