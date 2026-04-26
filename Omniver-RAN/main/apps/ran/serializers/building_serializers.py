from __future__ import annotations

from typing import Any

from main.apps.ran.serializers._base import Serializer


class BuildingWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        name = self._require(data, "name", str)
        pos_x = self._optional(data, "pos_x", (int, float), 0)
        pos_y = self._optional(data, "pos_y", (int, float), 0)
        pos_z = self._optional(data, "pos_z", (int, float), 0)
        size_x = self._optional(data, "size_x", (int, float), 10)
        size_y = self._optional(data, "size_y", (int, float), 10)
        size_z = self._optional(data, "size_z", (int, float), 10)
        color_r = self._optional(data, "color_r", (int, float), 0.75)
        color_g = self._optional(data, "color_g", (int, float), 0.75)
        color_b = self._optional(data, "color_b", (int, float), 0.75)
        usd_path = self._optional(data, "usd_path", str, "")
        target_height_m = self._optional(data, "target_height_m", (int, float), None)
        rot_x = self._optional(data, "rot_x", (int, float), 0)
        rot_y = self._optional(data, "rot_y", (int, float), 0)
        rot_z = self._optional(data, "rot_z", (int, float), 0)
        material = self._optional(data, "material", str, "")
        scene_id = self._optional(data, "scene_id", str, "")

        return {
            "name": name,
            "pos_x": float(pos_x),
            "pos_y": float(pos_y),
            "pos_z": float(pos_z),
            "size_x": float(size_x),
            "size_y": float(size_y),
            "size_z": float(size_z),
            "color_r": float(color_r),
            "color_g": float(color_g),
            "color_b": float(color_b),
            "usd_path": usd_path or "",
            "target_height_m": float(target_height_m) if target_height_m is not None else None,
            "rot_x": float(rot_x),
            "rot_y": float(rot_y),
            "rot_z": float(rot_z),
            "material": material or "",
            "scene_id": scene_id or "",
        }


class BuildingReadSerializer(Serializer):
    @classmethod
    def to_representation(cls, instance: Any) -> dict[str, Any]:
        return {
            "building_uuid": instance.building_uuid,
            "name": instance.name,
            "scene_id": instance.scene_id,
            "position": [instance.pos_x, instance.pos_y, instance.pos_z],
            "size": [instance.size_x, instance.size_y, instance.size_z],
            "color": [instance.color_r, instance.color_g, instance.color_b],
            "usd_path": instance.usd_path,
            "target_height_m": instance.target_height_m,
            "rotation_xyz_deg": [instance.rot_x, instance.rot_y, instance.rot_z],
            "material": instance.material,
            "created_at": instance.building_created_at.isoformat(),
            "updated_at": instance.building_updated_at.isoformat(),
        }
