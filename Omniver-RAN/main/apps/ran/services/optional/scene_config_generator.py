"""Scene configuration generator from DB models.

Generates scene_config.json-compatible dict from BuildingObject, GnbConfig,
and UeConfig DB records.
"""
from typing import Any, Optional

from main.apps.ran.models import (
    BuildingObject,
    GnbConfig,
    UeConfig,
)


# 全場景統一 USD — 強制 override,忽略 entity 自己的 usd_path,避免多種 USD 混雜
# 造成的渲染不一致 / 黑屏。對齊 asset registry preset:
#   - ue:       Office Woman   (preset_id=female_office)
#   - building: Brownstone 01  (preset_id=brownstone01)
#   - gnb:      Standard gNB   (preset_id=gnb_standard) — 注意 Kit _build_gnb 目前 ignore `usd`
#                              欄位,gNB 渲染仍走內建 cone+antenna 幾何;這個值寫上是給未來
#                              Kit 加 USD reference 用,以及讓 SceneLayoutReader 一致回報。
_FORCED_USD = {
    "ue":       "/app/assets/UE/female_office.usda",
    "building": "/app/assets/building/Brownstone01_Building.usda",
    "gnb":      "/omniverse/Library/gnb_standard.usda",
}


class SceneConfigGeneratorService:
    """Generate runtime scene configuration from database models."""

    @staticmethod
    def generate(scene_id: Optional[str] = None) -> dict[str, Any]:
        """Generate scene_config dict from DB models.

        Args:
            scene_id: Optional filter by scene_id. If None, returns all active records.

        Returns:
            Dict compatible with scene_config.json format (ground/buildings/gnbs/ues).
        """
        config = {
            "ground": {"material": "grass", "size": [1000, 1000]},
            "buildings": [],
            "gnbs": [],
            "ues": [],
        }

        # Query filter — only BuildingObject has scene_id
        building_filters = {} if scene_id is None else {"scene_id": scene_id}

        # Buildings
        buildings_qs = BuildingObject.objects.filter(**building_filters) if building_filters else BuildingObject.objects.all()
        for b in buildings_qs:
            building_entry = {
                "name": b.name,
                "position": [b.pos_x, b.pos_y, b.pos_z],
                "size": [b.size_x, b.size_y, b.size_z],
                "color": [b.color_r, b.color_g, b.color_b],
                "rotation_xyz_deg": [b.rot_x, b.rot_y, b.rot_z],
            }
            if _FORCED_USD["building"]:
                building_entry["usd"] = _FORCED_USD["building"]
            if b.target_height_m is not None:
                building_entry["target_height_m"] = b.target_height_m
            if b.material:
                building_entry["material"] = b.material
            config["buildings"].append(building_entry)

        # gNBs — no scene_id field, always fetch all
        gnbs_qs = GnbConfig.objects.all()
        for g in gnbs_qs:
            gnb_entry = {
                "name": g.name,
                "position": [g.pos_x, g.pos_y, g.pos_z],
                "color": [g.color_r, g.color_g, g.color_b],
                "frequency_ghz": g.freq_mhz / 1000.0,
                "power_dbm": g.power_dbm,
                "bandwidth_mhz": g.bw_hz / 1e6,
                "active": g.active,
            }
            if _FORCED_USD["gnb"]:
                gnb_entry["usd"] = _FORCED_USD["gnb"]
            if g.target_height_m is not None:
                gnb_entry["target_height_m"] = g.target_height_m
            if g.cells is not None:
                gnb_entry["cells"] = g.cells
            config["gnbs"].append(gnb_entry)

        # UEs — no scene_id field, always fetch all
        ues_qs = UeConfig.objects.all()
        for u in ues_qs:
            ue_entry = {
                "name": u.name,
                "prim_path": f"/World/{u.name}",
                "position": [u.pos_x, u.pos_y, u.pos_z],
                "color": [u.color_r, u.color_g, u.color_b],
                "speed_mps": u.speed_mps,
            }
            if _FORCED_USD["ue"]:
                ue_entry["usd"] = _FORCED_USD["ue"]
            if u.target_height_m is not None:
                ue_entry["target_height_m"] = u.target_height_m
            if u.waypoints_json:
                ue_entry["waypoints"] = u.waypoints_json
            config["ues"].append(ue_entry)

        return config
