from __future__ import annotations

from typing import Any

from main.apps.ran.serializers._base import Serializer


class ObstacleWriteSerializer(Serializer):
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
        material = self._optional(data, "material", str, "")
        usd_path = self._optional(data, "usd_path", str, "")
        scale_x = self._optional(data, "scale_x", (int, float), 1.0)
        scale_y = self._optional(data, "scale_y", (int, float), 1.0)
        scale_z = self._optional(data, "scale_z", (int, float), 1.0)
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
            "material": material or "",
            "usd_path": usd_path or "",
            "scale_x": float(scale_x),
            "scale_y": float(scale_y),
            "scale_z": float(scale_z),
            "scene_id": scene_id or "",
        }


class ObstacleReadSerializer(Serializer):
    @classmethod
    def to_representation(cls, instance: Any) -> dict[str, Any]:
        return {
            "obstacle_uuid": instance.obstacle_uuid,
            "name": instance.name,
            "scene_id": instance.scene_id,
            "position": [instance.pos_x, instance.pos_y, instance.pos_z],
            "size": [instance.size_x, instance.size_y, instance.size_z],
            "color": [instance.color_r, instance.color_g, instance.color_b],
            "material": instance.material,
            "usd_path": instance.usd_path,
            "scale": [instance.scale_x, instance.scale_y, instance.scale_z],
            "created_at": instance.obstacle_created_at.isoformat(),
            "updated_at": instance.obstacle_updated_at.isoformat(),
        }
