from __future__ import annotations

from typing import Any

from main.apps.ran.serializers._base import Serializer


class ObstacleWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        name = self._require(data, "name", str)

        # Handle position as array or individual fields
        position = self._optional(data, "position", (list, tuple))
        if position:
            pos_x = float(position[0]) if len(position) > 0 else 0
            pos_y = float(position[1]) if len(position) > 1 else 0
            pos_z = float(position[2]) if len(position) > 2 else 0
        else:
            pos_x = self._optional(data, "pos_x", (int, float), 0)
            pos_y = self._optional(data, "pos_y", (int, float), 0)
            pos_z = self._optional(data, "pos_z", (int, float), 0)

        # Handle size as array or individual fields
        size = self._optional(data, "size", (list, tuple))
        if size:
            size_x = float(size[0]) if len(size) > 0 else 10
            size_y = float(size[1]) if len(size) > 1 else 10
            size_z = float(size[2]) if len(size) > 2 else 10
        else:
            size_x = self._optional(data, "size_x", (int, float), 10)
            size_y = self._optional(data, "size_y", (int, float), 10)
            size_z = self._optional(data, "size_z", (int, float), 10)

        # Handle color as array or individual fields
        color = self._optional(data, "color", (list, tuple))
        if color:
            color_r = float(color[0]) if len(color) > 0 else 0.75
            color_g = float(color[1]) if len(color) > 1 else 0.75
            color_b = float(color[2]) if len(color) > 2 else 0.75
        else:
            color_r = self._optional(data, "color_r", (int, float), 0.75)
            color_g = self._optional(data, "color_g", (int, float), 0.75)
            color_b = self._optional(data, "color_b", (int, float), 0.75)

        material = self._optional(data, "material", str, "")
        usd_path = self._optional(data, "usd_path", str, "")

        # Handle scale as array or individual fields
        scale = self._optional(data, "scale", (list, tuple))
        if scale:
            scale_x = float(scale[0]) if len(scale) > 0 else 1.0
            scale_y = float(scale[1]) if len(scale) > 1 else 1.0
            scale_z = float(scale[2]) if len(scale) > 2 else 1.0
        else:
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
