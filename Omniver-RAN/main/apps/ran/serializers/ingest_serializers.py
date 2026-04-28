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
            position = s.get("position")  # [x, y, z] or None
            missing = [k for k, v in {"ue_name": ue_name, "serving_cell": serving_cell,
                                       "rsrp_dbm": rsrp_dbm, "sinr_db": sinr_db}.items() if v is None]
            if missing:
                self._add_error("signals", f"[{i}] missing: {missing}")
                continue
            if not isinstance(rsrp_map, dict):
                self._add_error("signals", f"[{i}] rsrp_map must be object")
                continue
            signal_data = {
                "ue_name": str(ue_name),
                "serving_cell": str(serving_cell),
                "rsrp_dbm": float(rsrp_dbm),
                "sinr_db": float(sinr_db),
                "rsrp_map": {str(k): float(v) for k, v in rsrp_map.items()},
            }
            # 加入位置（可選）
            if position is not None:
                if isinstance(position, list) and len(position) == 3:
                    try:
                        signal_data["position"] = [float(position[0]), float(position[1]), float(position[2])]
                    except (TypeError, ValueError):
                        self._add_error("signals", f"[{i}] position must be [x, y, z] floats")
                        continue
            cleaned.append(signal_data)
        return {"ts": ts, "session_uuid": session_uuid, "signals": cleaned}
