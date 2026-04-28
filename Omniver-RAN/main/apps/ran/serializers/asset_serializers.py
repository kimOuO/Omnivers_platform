from __future__ import annotations

from typing import Any

from main.apps.ran.serializers._base import Serializer


class UsdAssetReadSerializer(Serializer):
    @classmethod
    def to_representation(cls, instance: dict[str, Any] | Any) -> dict[str, Any]:
        if isinstance(instance, dict):
            return instance

        return {
            "asset_uuid": instance.asset_uuid,
            "object_type": instance.object_type,
            "preset_id": instance.preset_id,
            "label": instance.label,
            "description": instance.description,
            "usd_path": instance.usd_path,
            "default_size": instance.default_size,
            "default_color": instance.default_color,
            "default_scale": instance.default_scale,
            "default_rotation": instance.default_rotation,
            "active": instance.active,
            "created_at": instance.asset_created_at,
            "updated_at": instance.asset_updated_at,
        }


class UsdAssetWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        preset_id = self._require(data, "preset_id", str)
        object_type = self._require(data, "object_type", str)
        label = self._require(data, "label", str)
        usd_path = self._require(data, "usd_path", str)
        description = self._optional(data, "description", str, default="")
        default_size = self._optional(data, "default_size", (list, type(None)))
        default_color = self._optional(data, "default_color", (list, type(None)))
        default_scale = self._optional(data, "default_scale", (list, type(None)))

        return {
            "preset_id": preset_id,
            "object_type": object_type,
            "label": label,
            "usd_path": usd_path,
            "description": description,
            "default_size": default_size,
            "default_color": default_color,
            "default_scale": default_scale,
        }


class UsdAssetUpdateSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        preset_id = self._require(data, "preset_id", str)
        return {"preset_id": preset_id}

    def _validate_update(self, data: dict[str, Any]) -> dict[str, Any]:
        """Update allows only: label, description, default_size/color/scale, active"""
        result = {}

        if "label" in data:
            result["label"] = str(data["label"])
        if "description" in data:
            result["description"] = str(data["description"])
        if "default_size" in data and data["default_size"] is not None:
            result["default_size"] = data["default_size"]
        if "default_color" in data and data["default_color"] is not None:
            result["default_color"] = data["default_color"]
        if "default_scale" in data and data["default_scale"] is not None:
            result["default_scale"] = data["default_scale"]
        if "default_rotation" in data and data["default_rotation"] is not None:
            result["default_rotation"] = data["default_rotation"]
        if "active" in data:
            result["active"] = bool(data["active"])

        return result
