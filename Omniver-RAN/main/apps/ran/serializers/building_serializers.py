from __future__ import annotations

from typing import Any

from main.apps.ran.serializers._base import Serializer


class BuildingWriteSerializer(Serializer):
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

        usd_path = self._optional(data, "usd_path", str, "")
        target_height_m = self._optional(data, "target_height_m", (int, float), None)

        # Handle rotation as array or individual fields
        rotation = self._optional(data, "rotation_xyz_deg", (list, tuple))
        if rotation:
            rot_x = float(rotation[0]) if len(rotation) > 0 else 0
            rot_y = float(rotation[1]) if len(rotation) > 1 else 0
            rot_z = float(rotation[2]) if len(rotation) > 2 else 0
        else:
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
