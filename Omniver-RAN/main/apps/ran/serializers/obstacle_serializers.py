from __future__ import annotations

from typing import Any

from main.apps.ran.serializers._base import Serializer


def _lookup_preset_usd(preset_id: str, object_type: str = "obstacle") -> dict[str, Any]:
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
            "preset_type": preset_id,
        }
    except UsdAsset.DoesNotExist:
        return {}


class ObstacleWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        name = self._require(data, "name", str)
        preset_id = self._optional(data, "preset_id", str, None)

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

        # Handle preset_id → lookup usd_path + defaults
        if preset_id:
            preset_data = _lookup_preset_usd(preset_id, "obstacle")
            if not preset_data:
                self._add_error("preset_id", "Unknown preset_id")
                return {}
            # If not explicitly provided, use preset defaults
            if not size:
                preset_size = preset_data.get("default_size")
                if preset_size:
                    size_x, size_y, size_z = preset_size[0], preset_size[1], preset_size[2]
            if not color:
                preset_color = preset_data.get("default_color")
                if preset_color:
                    color_r, color_g, color_b = preset_color[0], preset_color[1], preset_color[2]
            if not scale:
                preset_scale = preset_data.get("default_scale")
                if preset_scale:
                    scale_x, scale_y, scale_z = preset_scale[0], preset_scale[1], preset_scale[2]
            usd_path = preset_data.get("usd_path", "")
            preset_type = preset_id
        else:
            usd_path = self._optional(data, "usd_path", str, "")
            preset_type = ""

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
            "preset_type": preset_type,
            "scale_x": float(scale_x),
            "scale_y": float(scale_y),
            "scale_z": float(scale_z),
            "scene_id": scene_id or "",
        }

    def _validate_update(self, data: dict[str, Any]) -> dict[str, Any]:
        """更新時只允許修改 USD 規範的屬性"""
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

        # Handle scale as array or individual fields
        scale = self._optional(data, "scale", (list, tuple))
        if scale:
            result["scale_x"] = float(scale[0]) if len(scale) > 0 else None
            result["scale_y"] = float(scale[1]) if len(scale) > 1 else None
            result["scale_z"] = float(scale[2]) if len(scale) > 2 else None
        else:
            if "scale_x" in data:
                result["scale_x"] = float(data["scale_x"])
            if "scale_y" in data:
                result["scale_y"] = float(data["scale_y"])
            if "scale_z" in data:
                result["scale_z"] = float(data["scale_z"])

        # Editable USD properties
        if "usd_path" in data:
            result["usd_path"] = data["usd_path"] or ""
        if "material" in data:
            result["material"] = data["material"] or ""

        # Remove None values
        return {k: v for k, v in result.items() if v is not None}


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
            "preset_type": instance.preset_type,
            "scale": [instance.scale_x, instance.scale_y, instance.scale_z],
            "created_at": instance.obstacle_created_at.isoformat(),
            "updated_at": instance.obstacle_updated_at.isoformat(),
        }
