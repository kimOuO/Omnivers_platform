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
            # 新格式欄位（Sionna payload）
            serving_gnb     = s.get("serving_gnb")
            serving_pci     = s.get("serving_pci")
            serving_cell_id = s.get("serving_cell_id")
            # 向後相容：舊格式用 serving_cell，新格式用 serving_gnb + serving_cell_id
            serving_cell = s.get("serving_cell") or serving_cell_id or serving_gnb
            rsrp_dbm = s.get("rsrp_dbm")
            sinr_db = s.get("sinr_db")
            rsrp_map = s.get("rsrp_map") or {}
            position = s.get("position")  # [x, y, z] or None
            missing = [k for k, v in {"ue_name": ue_name, "rsrp_dbm": rsrp_dbm,
                                       "sinr_db": sinr_db}.items() if v is None]
            if missing or serving_cell is None:
                all_missing = missing + (["serving_cell/serving_gnb"] if serving_cell is None else [])
                self._add_error("signals", f"[{i}] missing: {all_missing}")
                continue
            if not isinstance(rsrp_map, dict):
                self._add_error("signals", f"[{i}] rsrp_map must be object")
                continue
            signal_data = {
                "ue_name":      str(ue_name),
                "serving_cell": str(serving_cell),
                "rsrp_dbm":     float(rsrp_dbm),
                "sinr_db":      float(sinr_db),
                "rsrp_map":     {str(k): float(v) for k, v in rsrp_map.items()},
            }
            if serving_gnb is not None:
                signal_data["serving_gnb"] = str(serving_gnb)
            if serving_pci is not None:
                try:
                    signal_data["serving_pci"] = int(serving_pci)
                except (TypeError, ValueError):
                    pass
            if serving_cell_id is not None:
                signal_data["serving_cell_id"] = str(serving_cell_id)
            # 2026-05-17 #2: KPM 補完 wireless KPI (throughput/MCS/PRB/rank).
            # 由 Dashboard / RAN-sim 在 ingest 時帶上,讓 playback 能重現。
            for k, caster in (
                ("throughput_dl_mbps", float),
                ("throughput_ul_mbps", float),
                ("mcs_dl", int),
                ("prb_used_dl", int),
                ("mimo_rank", int),
            ):
                v = s.get(k)
                if v is not None:
                    try:
                        signal_data[k] = caster(v)
                    except (TypeError, ValueError):
                        pass
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
