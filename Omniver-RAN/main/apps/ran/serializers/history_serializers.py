from __future__ import annotations

from typing import Any

from main.apps.ran.models import PositionHistory, SignalHistory
from main.apps.ran.serializers._base import Serializer


class HistoryQueryWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        ue_name = self._require(data, "ue_name", str)
        since = self._optional(data, "since", str)
        return {"ue_name": ue_name, "since": since}


class PositionHistoryReadSerializer(Serializer):
    @classmethod
    def to_representation(cls, instance: PositionHistory) -> dict[str, Any]:
        return {
            "ts": instance.position_ts.isoformat(),
            "x": instance.x,
            "y": instance.y,
            "z": instance.z,
        }


class SignalHistoryReadSerializer(Serializer):
    @classmethod
    def to_representation(cls, instance: SignalHistory) -> dict[str, Any]:
        return {
            "ts": instance.signal_ts.isoformat(),
            "serving_cell": instance.serving_cell,
            "rsrp_dbm": instance.rsrp_dbm,
            "sinr_db": instance.sinr_db,
            "rsrp_map": instance.rsrp_map_json,
        }
