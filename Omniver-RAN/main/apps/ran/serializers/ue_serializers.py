from __future__ import annotations

from typing import Any

from main.apps.ran.models import UeState, UeConfig
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
        # Handle UeConfig ORM object (from database)
        if isinstance(instance, UeConfig):
            return {
                "name": instance.name,
                "position": [float(instance.pos_x or 0), float(instance.pos_y or 0), float(instance.pos_z or 0)],
                "waypoints": instance.waypoints_json,
                "speed_mps": float(instance.speed_mps or 1.0),
                "loop": bool(instance.loop),
                "target_height_m": instance.target_height_m,
            }

        # Handle UeState
        if isinstance(instance, UeState):
            return {
                "name": instance.name,
                "position": _as_xyz(instance.position_json),
                "serving_cell": instance.serving_cell,
                "rsrp_dbm": instance.rsrp_dbm,
                "sinr_db": instance.sinr_db,
            }

        # Handle dict coming from Kit proxy
        if isinstance(instance, dict):
            return {
                "name": instance.get("name"),
                "position": _as_xyz(instance.get("position")),
                "serving_cell": instance.get("serving_cell"),
                "rsrp_dbm": instance.get("rsrp_dbm"),
                "sinr_db": instance.get("sinr_db"),
            }

        return {}


class UeWriteSerializer(Serializer):
    """Serializer for creating a new UE."""
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any] | None:
        name = self._require(data, "name", str)
        if not name:
            self._errors["name"] = "required (str)"
            return None

        pos_raw = data.get("position")
        position = _as_xyz(pos_raw) if pos_raw is not None else _as_xyz([0, 0, 0])

        speed_mps = self._optional(data, "speed_mps", (int, float))
        waypoints = data.get("waypoints", [])
        loop = data.get("loop", True)
        target_height_m = self._optional(data, "target_height_m", (int, float), None)

        # Handle preset_id → lookup usd_path + defaults
        preset_id = self._optional(data, "preset_id", str, None)
        if preset_id:
            from main.apps.ran.models import UsdAsset
            try:
                asset = UsdAsset.objects.get(preset_id=preset_id, object_type="ue", active=True)
                usd_path = asset.usd_path
                preset_type = preset_id
            except UsdAsset.DoesNotExist:
                self._add_error("preset_id", "Unknown preset_id")
                return {}
        else:
            usd_path = self._optional(data, "usd_path", str, "")
            preset_type = ""

        # Default target_height_m based on preset if not provided
        if target_height_m is None:
            PRESET_TARGET_HEIGHTS = {
                "female_office": 50.0,
                "male_party": 34.0,
            }
            target_height_m = PRESET_TARGET_HEIGHTS.get(preset_id)

        return {
            "name": name,
            "pos_x": float(position["x"]),
            "pos_y": float(position["y"]),
            "pos_z": float(position["z"]),
            "speed_mps": float(speed_mps) if speed_mps else 1.0,
            "waypoints_json": waypoints if isinstance(waypoints, list) else [],
            "loop": bool(loop),
            "usd_path": usd_path,
            "preset_type": preset_type,
            "target_height_m": float(target_height_m) if target_height_m is not None else None,
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
