from __future__ import annotations

from typing import Any

from main.apps.ran.serializers._base import Serializer


def _lookup_preset_usd(preset_id: str, object_type: str = "building") -> dict[str, Any]:
    """Look up USD asset by preset_id and return usd_path + defaults"""
    from main.apps.ran.models import UsdAsset

    if not preset_id:
        return {}

    try:
        asset = UsdAsset.objects.get(preset_id=preset_id, object_type=object_type, active=True)
        return {
            "usd_path": asset.usd_path,
            "default_size": asset.default_size,
            "default_color": asset.default_color,
            "default_scale": asset.default_scale,
            "default_rotation": asset.default_rotation,
            "preset_type": preset_id,
        }
    except UsdAsset.DoesNotExist:
        return {}


class BuildingWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        name = self._require(data, "name", str)
        preset_id = self._optional(data, "preset_id", str, None)
        # Allow direct usd_path input from frontend
        usd_path = self._optional(data, "usd_path", str, None)

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

        # Handle preset_id → lookup usd_path + defaults (only if usd_path not provided)
        preset_data = {}
        preset_type = preset_id or ""
        if preset_id:
            preset_data = _lookup_preset_usd(preset_id, "building")
            if not preset_data:
                self._add_error("preset_id", "Unknown preset_id")
                return {}

        # If not explicitly provided, use preset defaults
        if not size and preset_data:
            preset_size = preset_data.get("default_size")
            if preset_size:
                size_x, size_y, size_z = preset_size[0], preset_size[1], preset_size[2]
        if not color and preset_data:
            preset_color = preset_data.get("default_color")
            if preset_color:
                color_r, color_g, color_b = preset_color[0], preset_color[1], preset_color[2]

        # Priority: use explicit usd_path from frontend, fallback to preset lookup
        if not usd_path and preset_data:
            usd_path = preset_data.get("usd_path", "")
        usd_path = usd_path or ""

        target_height_m = self._optional(data, "target_height_m", (int, float), None)

        # Default target_height_m based on preset if not provided
        if target_height_m is None:
            PRESET_TARGET_HEIGHTS = {
                "brownstone01": 400.0,
                "brownstone02": 400.0,
                "factory": 400.0,
                "female_office": 50.0,
                "male_party": 34.0,
            }
            target_height_m = PRESET_TARGET_HEIGHTS.get(preset_id)

        # Handle rotation as array or individual fields
        rotation = self._optional(data, "rotation_xyz_deg", (list, tuple))
        if rotation:
            rot_x = float(rotation[0]) if len(rotation) > 0 else -90
            rot_y = float(rotation[1]) if len(rotation) > 1 else 0
            rot_z = float(rotation[2]) if len(rotation) > 2 else 0
        else:
            rot_x = self._optional(data, "rot_x", (int, float), -90)
            rot_y = self._optional(data, "rot_y", (int, float), 0)
            rot_z = self._optional(data, "rot_z", (int, float), 0)

        # Apply preset default_rotation if no rotation explicitly provided
        if not rotation and preset_data:
            preset_rot = preset_data.get("default_rotation")
            if preset_rot:
                rot_x, rot_y, rot_z = preset_rot[0], preset_rot[1], preset_rot[2]

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
            "preset_type": preset_type,
            "target_height_m": float(target_height_m) if target_height_m is not None else None,
            "rot_x": float(rot_x),
            "rot_y": float(rot_y),
            "rot_z": float(rot_z),
            "material": material or "",
            "scene_id": scene_id or "",
        }

    def _validate_update(self, data: dict[str, Any]) -> dict[str, Any]:
        """更新時只允許修改 USD 規範的屬性（不含 name / UUID / scene_id）"""
        result = {}

        # Handle position as array or individual fields
        position = self._optional(data, "position", (list, tuple))
        if position:
            result["pos_x"] = float(position[0]) if len(position) > 0 else None
            result["pos_y"] = float(position[1]) if len(position) > 1 else None
            result["pos_z"] = float(position[2]) if len(position) > 2 else None
        else:
            if "pos_x" in data:
                result["pos_x"] = float(data["pos_x"])
            if "pos_y" in data:
                result["pos_y"] = float(data["pos_y"])
            if "pos_z" in data:
                result["pos_z"] = float(data["pos_z"])

        # Handle size as array or individual fields
        size = self._optional(data, "size", (list, tuple))
        if size:
            result["size_x"] = float(size[0]) if len(size) > 0 else None
            result["size_y"] = float(size[1]) if len(size) > 1 else None
            result["size_z"] = float(size[2]) if len(size) > 2 else None
        else:
            if "size_x" in data:
                result["size_x"] = float(data["size_x"])
            if "size_y" in data:
                result["size_y"] = float(data["size_y"])
            if "size_z" in data:
                result["size_z"] = float(data["size_z"])

        # Handle color as array or individual fields
        color = self._optional(data, "color", (list, tuple))
        if color:
            result["color_r"] = float(color[0]) if len(color) > 0 else None
            result["color_g"] = float(color[1]) if len(color) > 1 else None
            result["color_b"] = float(color[2]) if len(color) > 2 else None
        else:
            if "color_r" in data:
                result["color_r"] = float(data["color_r"])
            if "color_g" in data:
                result["color_g"] = float(data["color_g"])
            if "color_b" in data:
                result["color_b"] = float(data["color_b"])

        # Handle rotation as array or individual fields
        rotation = self._optional(data, "rotation_xyz_deg", (list, tuple))
        if rotation:
            result["rot_x"] = float(rotation[0]) if len(rotation) > 0 else None
            result["rot_y"] = float(rotation[1]) if len(rotation) > 1 else None
            result["rot_z"] = float(rotation[2]) if len(rotation) > 2 else None
        else:
            if "rot_x" in data:
                result["rot_x"] = float(data["rot_x"])
            if "rot_y" in data:
                result["rot_y"] = float(data["rot_y"])
            if "rot_z" in data:
                result["rot_z"] = float(data["rot_z"])

        # Editable USD properties
        if "usd_path" in data:
            result["usd_path"] = data["usd_path"] or ""
        if "material" in data:
            result["material"] = data["material"] or ""
        if "target_height_m" in data and data["target_height_m"] is not None:
            result["target_height_m"] = float(data["target_height_m"])

        # Remove None values
        return {k: v for k, v in result.items() if v is not None}


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
            "preset_type": instance.preset_type,
            "target_height_m": instance.target_height_m,
            "rotation_xyz_deg": [instance.rot_x, instance.rot_y, instance.rot_z],
            "material": instance.material,
            "created_at": instance.building_created_at.isoformat(),
            "updated_at": instance.building_updated_at.isoformat(),
        }
