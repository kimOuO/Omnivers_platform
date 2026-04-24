"""PayloadTranslator — Omniverse ↔ ranp-sim JSON 格式互轉。

純 stateless 函式，不碰 DB / HTTP / settings。

三個方向：
  1. Kit UE read result → ranp-sim ComputeRunner  `ue_positions`
  2. ranp-sim ComputeRunner output → Omniverse IngestBusinessService `signals`
  3. scene snapshot (DB) → ranp-sim push_scene  body（full mode）
"""
from __future__ import annotations

from typing import Any


class PayloadTranslator:

    # -----------------------------------------------------------------
    # 1) Kit UE snapshot → ranp-sim ue_positions
    # -----------------------------------------------------------------
    @staticmethod
    def kit_ues_to_ranpsim_positions(kit_ues: Any) -> list[dict[str, Any]]:
        """從 `KitBusinessService.list_ues()` 結果拆出 ue_positions。

        Kit 可能回：
          - list of {name, position, velocity?, role?, qos_5qi?}
          - dict 以 name 為 key，值為 payload

        ranp-sim 要：
          [{"id", "position": [x,y,z], "velocity": [...]}, ...]
        """
        if isinstance(kit_ues, dict):
            items = [{"name": name, **(payload if isinstance(payload, dict) else {})}
                     for name, payload in kit_ues.items()]
        elif isinstance(kit_ues, list):
            items = kit_ues
        else:
            items = []

        result: list[dict[str, Any]] = []
        for u in items:
            name = u.get("name") or u.get("ue_name") or u.get("id")
            if not name:
                continue
            pos_raw = u.get("position")
            if isinstance(pos_raw, dict):
                pos = [
                    float(pos_raw.get("x", 0.0)),
                    float(pos_raw.get("y", 0.0)),
                    float(pos_raw.get("z", 0.0)),
                ]
            elif isinstance(pos_raw, (list, tuple)):
                pos = [float(p) for p in list(pos_raw)[:3]]
                while len(pos) < 3:
                    pos.append(0.0)
            else:
                pos = [
                    float(u.get("x", 0.0)),
                    float(u.get("y", 0.0)),
                    float(u.get("z", 0.0)),
                ]

            vel_raw = u.get("velocity") or [0.0, 0.0, 0.0]
            if isinstance(vel_raw, dict):
                vel = [
                    float(vel_raw.get("x", 0.0)),
                    float(vel_raw.get("y", 0.0)),
                    float(vel_raw.get("z", 0.0)),
                ]
            else:
                vel = [float(v) for v in (list(vel_raw) + [0.0, 0.0, 0.0])[:3]]

            entry: dict[str, Any] = {
                "id": name,
                "position": pos,
                "velocity": vel,
            }
            if "role" in u:
                entry["role"] = int(u["role"])
            if "qos_5qi" in u:
                entry["qos_5qi"] = int(u["qos_5qi"])
            result.append(entry)
        return result

    # -----------------------------------------------------------------
    # 2) ranp-sim ComputeRunner output → IngestBusinessService signals
    # -----------------------------------------------------------------
    @staticmethod
    def ranpsim_output_to_signals(ranpsim_compute_data: dict) -> list[dict[str, Any]]:
        """從 ranp-sim `data.ue_status[]` 轉成 Omniverse 內用的 signals list。

        ranp-sim 輸出一筆 ue_status：
          {ue_id, serving_gnb, rsrp_dbm, sinr_db, all_rsrp: {gNB_1: -82.3, ...}}

        轉為 Omniverse 格式：
          {ue_name, serving_cell, rsrp_dbm, sinr_db, rsrp_map}
        """
        ue_status_list = ranpsim_compute_data.get("ue_status") or []
        signals: list[dict[str, Any]] = []
        for ue in ue_status_list:
            ue_name = ue.get("ue_id") or ue.get("name")
            serving = ue.get("serving_gnb") or ue.get("serving_cell")
            if not ue_name or not serving:
                continue
            signals.append({
                "ue_name": str(ue_name),
                "serving_cell": str(serving),
                "rsrp_dbm": float(ue.get("rsrp_dbm", 0.0)),
                "sinr_db": float(ue.get("sinr_db", 0.0)),
                "rsrp_map": {
                    str(k): float(v) for k, v in (ue.get("all_rsrp") or {}).items()
                },
            })
        return signals

    # -----------------------------------------------------------------
    # 3) SceneSnapshot → ranp-sim push_scene body (full mode)
    # -----------------------------------------------------------------
    @staticmethod
    def snapshot_to_ranpsim_push_scene(
        scene_id: str,
        config_json: dict,
        *,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        """產出 ranp-sim `/ConfigManager/push_scene` full-override body。"""
        buildings = [
            {
                "name": b.get("name", f"bld_{i}"),
                "position": b.get("position", [0, 0, 0]),
                "size": b.get("size", [1, 1, 1]),
                "material": b.get("material", "concrete"),
            }
            for i, b in enumerate(config_json.get("buildings", []))
        ]
        ground_src = config_json.get("ground") or {}
        ground = {
            "position": ground_src.get("position", [0, 0, 0]),
            "size": ground_src.get("size", [250, 250]),
        }

        gnbs: list[dict[str, Any]] = []
        for g in config_json.get("gnbs", []):
            gnbs.append({
                "name": g["name"],
                "pci": int(g.get("pci", 0)),
                "cell_id": str(g.get("cell_id", "")),
                "position": g.get("position", [0, 0, 0]),
                "frequency_ghz": float(g.get("frequency_ghz", 3.5)),
                "power_dbm": float(g.get("power_dbm", 43)),
                "bandwidth_mhz": float(g.get("bandwidth_mhz", 100)),
            })

        ues = [
            {
                "name": u["name"],
                "qos_5qi": int(u.get("qos_5qi", 9)),
                "role": int(u.get("role", 1)),
            }
            for u in config_json.get("ues", [])
        ]

        payload: dict[str, Any] = {
            "scene_id": scene_id,
            "override_mode": "full",
            "geometry_source": {
                "type": "buildings_json",
                "buildings": buildings,
                "ground": ground,
            },
            "gnbs": gnbs,
            "ues": ues,
        }
        if ttl_seconds is not None:
            payload["ttl_seconds"] = int(ttl_seconds)
        return payload
