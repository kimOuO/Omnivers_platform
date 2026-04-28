from __future__ import annotations

from typing import Any

from main.apps.ran.models import GnbConfig
from main.apps.ran.serializers._base import Serializer


def _as_xyz(v: Any) -> dict[str, float]:
    if isinstance(v, dict):
        return {"x": float(v.get("x", 0)), "y": float(v.get("y", 0)), "z": float(v.get("z", 0))}
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return {"x": float(v[0]), "y": float(v[1]), "z": float(v[2])}
    return {"x": 0.0, "y": 0.0, "z": 0.0}


def _as_list(v: Any) -> list[float]:
    if isinstance(v, dict):
        return [float(v.get("x", 0)), float(v.get("y", 0)), float(v.get("z", 0))]
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return [float(v[0]), float(v[1]), float(v[2])]
    return [0.0, 0.0, 0.0]


class GnbReadSerializer(Serializer):
    @classmethod
    def to_representation(cls, instance: Any) -> dict[str, Any]:
        # Handle GnbConfig ORM object
        if isinstance(instance, GnbConfig):
            return {
                "gnb_uuid": instance.gnb_uuid,
                "name": instance.name,
                "position": [float(instance.pos_x or 0), float(instance.pos_y or 0), float(instance.pos_z or 0)],
                "frequency_ghz": float((instance.freq_mhz or 0) / 1000.0),
                "power_dbm": float(instance.power_dbm or 0),
                "bandwidth_mhz": float((instance.bw_hz or 0) / 1_000_000.0),
                "active": bool(instance.active),
                "cells": instance.cells or [],
                "created_at": instance.gnb_created_at.isoformat() if instance.gnb_created_at else None,
                "updated_at": instance.gnb_updated_at.isoformat() if instance.gnb_updated_at else None,
            }

        # Handle dict (from Kit)
        if isinstance(instance, dict):
            freq_mhz = instance.get("freq_mhz")
            if freq_mhz is None and "frequency_ghz" in instance:
                freq_mhz = float(instance["frequency_ghz"]) * 1000.0
            bw_hz = instance.get("bw_hz")
            if bw_hz is None and "bandwidth_mhz" in instance:
                bw_hz = float(instance["bandwidth_mhz"]) * 1_000_000.0
            return {
                "name": instance.get("name"),
                "position": _as_xyz(instance.get("position") or instance.get("pos")),
                "frequency_ghz": float((freq_mhz or 0) / 1000.0),
                "power_dbm": float(instance.get("power_dbm") or 0),
                "bandwidth_mhz": float((bw_hz or 0) / 1_000_000.0),
                "active": bool(instance.get("active", True)),
                "cells": instance.get("cells") or [],
            }

        return {}


class GnbWriteSerializer(Serializer):
    """Serializer for creating a new gNB."""
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any] | None:
        name = self._require(data, "name", str)
        if not name:
            self._errors["name"] = "required (str)"
            return None

        pos_raw = data.get("position")
        position = _as_xyz(pos_raw) if pos_raw is not None else _as_xyz([0, 0, 0])

        freq_mhz = self._optional(data, "frequency_ghz", (int, float))
        bw_mhz = self._optional(data, "bandwidth_mhz", (int, float))
        power_dbm = self._optional(data, "power_dbm", (int, float))

        return {
            "name": name,
            "pos_x": float(position["x"]),
            "pos_y": float(position["y"]),
            "pos_z": float(position["z"]),
            "freq_mhz": float(freq_mhz * 1000.0) if freq_mhz else 3500.0,
            "bw_hz": float(bw_mhz * 1_000_000.0) if bw_mhz else 100_000_000.0,
            "power_dbm": float(power_dbm) if power_dbm else 43,
            "active": data.get("active", True),
            "cells": data.get("cells") or [],
        }


class GnbStateWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        name = self._require(data, "name", str)
        power_dbm = self._optional(data, "power_dbm", (int, float))
        active = self._optional(data, "active", bool)
        freq_ghz = self._optional(data, "frequency_ghz", (int, float))
        bw_mhz = self._optional(data, "bandwidth_mhz", (int, float))
        pos_raw = data.get("position")  # [x,y,z] or {"x","y","z"} or None
        position = _as_xyz(pos_raw) if pos_raw is not None else None
        return {
            "name": name,
            "power_dbm": float(power_dbm) if power_dbm is not None else None,
            "active": active,
            "frequency_ghz": float(freq_ghz) if freq_ghz is not None else None,
            "bandwidth_mhz": float(bw_mhz) if bw_mhz is not None else None,
            "position": position,
        }

    def _validate_update(self, data: dict[str, Any]) -> dict[str, Any]:
        """更新時只允許修改 USD 規範的屬性"""
        result = {}

        # Handle position
        if "position" in data:
            pos_raw = data.get("position")
            position = _as_xyz(pos_raw) if pos_raw is not None else None
            if position:
                result["position"] = position

        # Editable RF parameters
        if "power_dbm" in data:
            result["power_dbm"] = float(data["power_dbm"])
        if "frequency_ghz" in data:
            result["frequency_ghz"] = float(data["frequency_ghz"])
        if "bandwidth_mhz" in data:
            result["bandwidth_mhz"] = float(data["bandwidth_mhz"])
        if "active" in data:
            result["active"] = bool(data["active"])

        # Color (USD display property)
        if "color" in data:
            color = data["color"]
            if isinstance(color, (list, tuple)) and len(color) >= 3:
                result["color_r"] = float(color[0])
                result["color_g"] = float(color[1])
                result["color_b"] = float(color[2])

        # Height for antenna placement
        if "target_height_m" in data and data["target_height_m"] is not None:
            result["target_height_m"] = float(data["target_height_m"])

        # Cells array (multiple sectors with pci + azimuth)
        if "cells" in data:
            result["cells"] = data["cells"] or []

        return result
