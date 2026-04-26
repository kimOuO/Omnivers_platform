"""External system operations — Kit Render Server (port 8080).

Per backend_rule.md §14-2: 外部系統類型對象 → `<system_name>_operations.py`.
"""
from __future__ import annotations

from typing import Any

import requests
from django.conf import settings


class KitBusinessService:
    """Thin synchronous HTTP client. Raises requests.HTTPError on non-2xx."""

    @staticmethod
    def _url(path: str) -> str:
        base = getattr(settings, "KIT_BASE_URL", "http://localhost:8080")
        return f"{base.rstrip('/')}{path}"

    @staticmethod
    def _post(path: str, body: dict[str, Any] | None = None, timeout: float = 5.0) -> Any:
        r = requests.post(KitBusinessService._url(path), json=body or {}, timeout=timeout)
        r.raise_for_status()
        if r.status_code == 204 or not r.content:
            return None
        return r.json()

    @staticmethod
    def _get(path: str, timeout: float = 5.0) -> Any:
        r = requests.get(KitBusinessService._url(path), timeout=timeout)
        r.raise_for_status()
        return r.json()

    # ---- Scene ----

    @staticmethod
    def get_scene_status() -> dict[str, Any]:
        return KitBusinessService._get("/scene/status")

    @staticmethod
    def get_scene_layout() -> dict[str, Any]:
        return KitBusinessService._get("/scene/layout")

    @staticmethod
    def build_scene() -> None:
        KitBusinessService._post("/scene/build")

    @staticmethod
    def push_scene_config(config_dict: dict[str, Any]) -> None:
        KitBusinessService._post("/scene/config", config_dict)

    @staticmethod
    def clear_scene() -> None:
        KitBusinessService._post("/scene/clear")

    @staticmethod
    def start_animation() -> None:
        KitBusinessService._post("/animation/start")

    @staticmethod
    def stop_animation() -> None:
        KitBusinessService._post("/animation/stop")

    # ---- UE ----

    @staticmethod
    def list_ues() -> Any:
        return KitBusinessService._get("/ues")

    @staticmethod
    def move_ue(name: str, x: float, y: float, z: float) -> None:
        KitBusinessService._post(f"/ue/{name}/move", {"x": x, "y": y, "z": z})

    @staticmethod
    def set_trajectory(name: str, waypoints: list[list[float]], speed_mps: float, loop: bool = True) -> None:
        KitBusinessService._post(
            f"/ue/{name}/trajectory",
            {"waypoints": waypoints, "speed_mps": speed_mps, "loop": loop},
        )

    @staticmethod
    def push_signal(
        name: str,
        serving_cell: str,
        rsrp_dbm: float,
        sinr_db: float,
        rsrp_map: dict[str, float],
    ) -> None:
        KitBusinessService._post(
            f"/ue/{name}/signal",
            {
                "serving_cell": serving_cell,
                "rsrp_dbm": rsrp_dbm,
                "sinr_db": sinr_db,
                "rsrp_map": rsrp_map,
            },
        )

    # ---- gNB ----

    @staticmethod
    def list_gnbs() -> list[dict[str, Any]]:
        return KitBusinessService._get("/gnbs")

    @staticmethod
    def update_gnb(name: str, changes: dict[str, Any]) -> None:
        """Push field changes (power_dbm / active / frequency_ghz / bandwidth_mhz / position)
        to Kit. Only keys actually present in `changes` are sent — Kit applies what it knows."""
        if not changes:
            return
        KitBusinessService._post(f"/gnb/{name}/update", changes)
