"""External system operations — ranp-sim (port 8000).

Per backend_rule.md §14-2: 外部系統類型對象 → `<system_name>_operations.py`.

Omniverse 直接呼叫 ranp-sim，不再經 dt-ueinference 中介。
"""
from __future__ import annotations

from typing import Any

import requests

from main.utils.env_loader import get_str
from main.utils.logger import get_logger

log = get_logger(__name__)

_DEFAULT_BASE = "http://host.docker.internal:8000"
_DEFAULT_TIMEOUT = 10.0
_PUSH_SCENE_TIMEOUT = 30.0  # Sionna engine 重建 2–5 s


class RanpsimBusinessService:
    """Thin synchronous HTTP client. Raises requests.HTTPError on non-2xx."""

    @staticmethod
    def _base() -> str:
        return get_str("RANPSIM_BASE_URL", _DEFAULT_BASE).rstrip("/")

    @staticmethod
    def _timeout() -> float:
        return float(get_str("RANPSIM_TIMEOUT_SEC", str(_DEFAULT_TIMEOUT)))

    @staticmethod
    def _post(path: str, body: dict[str, Any] | None = None,
              *, timeout: float | None = None) -> Any:
        url = f"{RanpsimBusinessService._base()}{path}"
        r = requests.post(
            url,
            json=body or {},
            timeout=timeout or RanpsimBusinessService._timeout(),
        )
        r.raise_for_status()
        if r.status_code == 204 or not r.content:
            return None
        return r.json()

    # ---- Config (scene override) ----

    @staticmethod
    def push_scene(
        scene_id: str,
        gnbs: list[dict[str, Any]],
        *,
        override_mode: str = "ran_only",
        buildings: list[dict[str, Any]] | None = None,
        ues: list[dict[str, Any]] | None = None,
        ttl_seconds: int | None = None,
    ) -> Any:
        """Runtime scene override.

        Args:
            scene_id: scene identifier (must match ranp-sim's current scene).
            gnbs: **full** gNB list (override_mode=ran_only 整批覆蓋，
                  部分列表會把其他 gNB 刪掉).
            override_mode: "ran_only" | "full" | "none"
            buildings / ues: full mode 才需要；ran_only 可省
            ttl_seconds: override 存活時間；省略則走 ranp-sim 預設
        """
        payload: dict[str, Any] = {
            "scene_id": scene_id,
            "override_mode": override_mode,
            "gnbs": gnbs,
        }
        if buildings is not None:
            payload.setdefault("geometry_source", {})["buildings"] = buildings
        if ues is not None:
            payload["ues"] = ues
        if ttl_seconds is not None:
            payload["ttl_seconds"] = ttl_seconds
        return RanpsimBusinessService._post(
            "/api/v0.1/RanpSim/RanSignal/ConfigManager/push_scene",
            payload,
            timeout=_PUSH_SCENE_TIMEOUT,
        )

    @staticmethod
    def reset_to_default() -> Any:
        return RanpsimBusinessService._post(
            "/api/v0.1/RanpSim/RanSignal/ConfigManager/reset_to_default",
            {},
            timeout=_PUSH_SCENE_TIMEOUT,
        )

    # ---- Compute ----

    @staticmethod
    def compute(
        scene_id: str,
        timestamp_ms: int,
        ue_positions: list[dict[str, Any]],
    ) -> Any:
        """Per-tick compute: RSRP/SINR/MCS/throughput for each UE.

        ue_positions: [{id, position:[x,y,z], velocity:[...], qos_5qi?}]
        """
        return RanpsimBusinessService._post(
            "/api/v0.1/RanpSim/RanSignal/ComputeRunner/compute",
            {
                "scene_id": scene_id,
                "timestamp_ms": timestamp_ms,
                "ue_positions": ue_positions,
            },
        )

    # ---- Health ----

    @staticmethod
    def health() -> Any:
        return RanpsimBusinessService._post(
            "/api/v0.1/RanpSim/RanSignal/HealthChecker/read", {}
        )
