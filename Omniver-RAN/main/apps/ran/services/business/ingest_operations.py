"""IngestBusinessService — in-process 訊號 ingest 核心邏輯。

把原本在 `SignalIngestor.create` Actor 裡的 DB 寫入 + Kit push 抽出來，
讓 HTTP Actor 和 tick_loop management command 都能共用，
tick loop 不必繞 HTTP 打自己。

Per backend_rule.md §2-1：Actor = 薄殼，核心邏輯走 Business Service。
"""
from __future__ import annotations

from typing import Any

from django.db import transaction

from main.apps.ran.models import SignalHistory, UeState, PositionHistory
from main.apps.ran.services.business.kit_operations import KitBusinessService
from main.apps.ran.services.business.sqldb_operations import SqlDbBusinessService
from main.apps.ran.services.common.timestamp_service import TimestampService
from main.apps.ran.services.common.uuid_service import UUIDService
from main.utils.logger import get_logger

log = get_logger(__name__)


class IngestBusinessService:
    """In-process signal ingest. 同一份邏輯被 HTTP Actor 與 tick 背景任務共用。"""

    @staticmethod
    @transaction.atomic
    def ingest_signals(signals: list[dict[str, Any]], ts=None, session_uuid=None) -> dict[str, int]:
        """寫入 signal_history / ue_state / position_history 並 push 給 Kit。

        Args:
            signals: [{ue_name, serving_cell, rsrp_dbm, sinr_db, rsrp_map, position?}, ...]
                     已 validate 過的乾淨資料。position 可選，為 [x, y, z]。
            ts: 時間戳 (datetime) — 不給則用現在
            session_uuid: 可選，來自 RAN-sim 的 session identifier

        Returns:
            {"accepted": N, "kit_errors": K}
        """
        ts = ts or TimestampService.get_current_timestamp()
        kit_errors = 0

        for sig in signals:
            # 1. 歷史
            SqlDbBusinessService.create_entity(
                SignalHistory,
                {
                    "session_uuid": session_uuid,
                    "signal_uuid": UUIDService.random_uuid(),
                    "ue_name": sig["ue_name"],
                    "serving_cell": sig["serving_cell"],
                    "rsrp_dbm": sig["rsrp_dbm"],
                    "sinr_db": sig["sinr_db"],
                    "rsrp_map_json": sig["rsrp_map"],
                    "signal_ts": ts,
                },
            )
            # 1b. 位置歷史（若提供）
            if "position" in sig and sig["position"] is not None:
                position = sig["position"]
                if isinstance(position, list) and len(position) == 3:
                    SqlDbBusinessService.create_entity(
                        PositionHistory,
                        {
                            "session_uuid": session_uuid,
                            "entity_name": sig["ue_name"],
                            "entity_type": "ue",
                            "x": float(position[0]),
                            "y": float(position[1]),
                            "z": float(position[2]),
                        },
                    )
            # 2. 最新快照 upsert
            SqlDbBusinessService.upsert_entity(
                UeState,
                lookup={"name": sig["ue_name"]},
                defaults={
                    "serving_cell": sig["serving_cell"],
                    "rsrp_dbm": sig["rsrp_dbm"],
                    "sinr_db": sig["sinr_db"],
                },
            )
            # 3. 推 Kit（HUD 顏色編碼）
            try:
                KitBusinessService.push_signal(
                    sig["ue_name"], sig["serving_cell"], sig["rsrp_dbm"],
                    sig["sinr_db"], sig["rsrp_map"],
                )
            except Exception as e:  # noqa: BLE001
                kit_errors += 1
                log.warning("push_signal(%s) failed: %s", sig["ue_name"], e)

        return {"accepted": len(signals), "kit_errors": kit_errors}
