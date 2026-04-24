from __future__ import annotations

from typing import Any

from main.apps.ran.models import PlatformEvent
from main.apps.ran.serializers._base import Serializer


class PlatformReportWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        event = self._require(data, "event", str)
        payload = self._require(data, "payload", dict)
        return {"event": event, "payload": payload or {}}


class PlatformEventReadSerializer(Serializer):
    @classmethod
    def to_representation(cls, instance: PlatformEvent) -> dict[str, Any]:
        return {
            "event_uuid": instance.event_uuid,
            "event": instance.event,
            "payload": instance.payload_json,
            "ts": instance.event_ts.isoformat(),
        }
