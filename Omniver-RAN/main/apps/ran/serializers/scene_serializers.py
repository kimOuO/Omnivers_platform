from __future__ import annotations

from typing import Any

from main.apps.ran.serializers._base import Serializer


class SceneOverviewReadSerializer(Serializer):
    @classmethod
    def to_representation(cls, instance: dict[str, Any]) -> dict[str, Any]:
        return {
            "buildings": int(instance.get("buildings", 0) or 0),
            "gnbs": int(instance.get("gnbs", 0) or 0),
            "ues": int(instance.get("ues", 0) or 0),
            "animating": bool(instance.get("animating", False)),
        }


class SceneInitWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        scene_id = self._require(data, "scene_id", str)
        buildings = self._optional(data, "buildings", list, default=[])
        gnbs = self._optional(data, "gnbs", list, default=[])
        ues = self._optional(data, "ues", list, default=[])
        return {"scene_id": scene_id, "buildings": buildings, "gnbs": gnbs, "ues": ues}


class SceneLayoutReadSerializer(Serializer):
    @classmethod
    def to_representation(cls, instance: dict[str, Any]) -> dict[str, Any]:
        return {
            "buildings": instance.get("buildings") or [],
            "gnbs": instance.get("gnbs") or [],
            "ues": instance.get("ues") or [],
            "ground": instance.get("ground") or {},
        }
