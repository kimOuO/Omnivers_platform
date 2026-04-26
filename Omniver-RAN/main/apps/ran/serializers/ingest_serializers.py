from __future__ import annotations

from typing import Any

from main.apps.ran.serializers._base import Serializer


class SignalBatchWriteSerializer(Serializer):
    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:
        ts = self._optional(data, "ts", str)
        session_uuid = self._optional(data, "session_uuid", str)
        signals = self._require(data, "signals", list)
        if signals is None:
            return {"ts": ts, "session_uuid": session_uuid, "signals": []}
        cleaned: list[dict[str, Any]] = []
        for i, s in enumerate(signals):
            if not isinstance(s, dict):
                self._add_error("signals", f"[{i}] must be object")
                continue
            ue_name = s.get("ue_name")
            serving_cell = s.get("serving_cell")
            rsrp_dbm = s.get("rsrp_dbm")
            sinr_db = s.get("sinr_db")
            rsrp_map = s.get("rsrp_map") or {}
            missing = [k for k, v in {"ue_name": ue_name, "serving_cell": serving_cell,
                                       "rsrp_dbm": rsrp_dbm, "sinr_db": sinr_db}.items() if v is None]
            if missing:
                self._add_error("signals", f"[{i}] missing: {missing}")
                continue
            if not isinstance(rsrp_map, dict):
                self._add_error("signals", f"[{i}] rsrp_map must be object")
                continue
            cleaned.append({
                "ue_name": str(ue_name),
                "serving_cell": str(serving_cell),
                "rsrp_dbm": float(rsrp_dbm),
                "sinr_db": float(sinr_db),
                "rsrp_map": {str(k): float(v) for k, v in rsrp_map.items()},
            })
        return {"ts": ts, "session_uuid": session_uuid, "signals": cleaned}
