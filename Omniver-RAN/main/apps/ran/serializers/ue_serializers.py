from __future__ import annotations

from typing import Any

from main.apps.ran.models import UeState
from main.apps.ran.serializers._base import Serializer


def _as_xyz(v: Any) -> dict[str, float]:
    if isinstance(v, dict):
        return {"x": float(v.get("x", 0)), "y": float(v.get("y", 0)), "z": float(v.get("z", 0))}
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return {"x": float(v[0]), "y": float(v[1]), "z": float(v[2])}
    return {"x": 0.0, "y": 0.0, "z": 0.0}


class UeReadSerializer(Serializer):
    @classmethod
    def to_representation(cls, instance: Any) -> dict[str, Any]:
        if isinstance(instance, UeState):
            return {
                "name": instance.name,
                "position": _as_xyz(instance.position_json),
                "serving_cell": instance.serving_cell,
                "rsrp_dbm": instance.rsrp_dbm,
                "sinr_db": instance.sinr_db,
            }
        # Raw dict coming from Kit proxy
        name = instance.get("name") if isinstance(instance, dict) else None
        return {
            "name": name,
            "position": _as_xyz(instance.get("position") if isinstance(instance, dict) else None),
            "serving_cell": instance.get("serving_cell") if isinstance(instance, dict) else None,
            "rsrp_dbm": instance.get("rsrp_dbm") if isinstance(instance, dict) else None,
            "sinr_db": instance.get("sinr_db") if isinstance(instance, dict) else None,
        }


class UeMoveWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        name = self._require(data, "name", str)
        x = self._require(data, "x", (int, float))
        z = self._require(data, "z", (int, float))
        y = self._optional(data, "y", (int, float), default=0.0)
        return {"name": name, "x": float(x or 0), "y": float(y or 0), "z": float(z or 0)}


class UeTrajectoryWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        name = self._require(data, "name", str)
        waypoints = self._require(data, "waypoints", list)
        speed_mps = self._require(data, "speed_mps", (int, float))
        loop = self._optional(data, "loop", bool, default=True)
        if waypoints is not None:
            if len(waypoints) < 2:
                self._add_error("waypoints", "need at least 2 points")
            else:
                for i, wp in enumerate(waypoints):
                    if not (isinstance(wp, list) and len(wp) == 3):
                        self._add_error("waypoints", f"[{i}] must be [x, y, z]")
                        break
        if speed_mps is not None and speed_mps <= 0:
            self._add_error("speed_mps", "must be > 0")
        return {
            "name": name,
            "waypoints": waypoints or [],
            "speed_mps": float(speed_mps or 0),
            "loop": bool(loop),
        }
