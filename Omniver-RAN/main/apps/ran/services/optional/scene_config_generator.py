"""Scene configuration generator from DB models.

Generates scene_config.json-compatible dict from BuildingObject, ObstacleObject,
GnbConfig, and UeConfig DB records.
"""
from typing import Any, Optional

from main.apps.ran.models import (
    BuildingObject,
    ObstacleObject,
    GnbConfig,
    UeConfig,
)


class SceneConfigGeneratorService:
    """Generate runtime scene configuration from database models."""

    @staticmethod
    def generate(scene_id: Optional[str] = None) -> dict[str, Any]:
        """Generate scene_config dict from DB models.

        Args:
            scene_id: Optional filter by scene_id. If None, returns all active records.

        Returns:
            Dict compatible with scene_config.json format (ground/buildings/gnbs/ues/obstacles).
        """
        config = {
            "ground": {"material": "grass", "size": [1000, 1000]},
            "buildings": [],
            "gnbs": [],
            "ues": [],
            "obstacles": [],
        }

        # Query filters — only BuildingObject and ObstacleObject have scene_id
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
            if b.usd_path:
                building_entry["usd"] = b.usd_path
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
            if g.target_height_m is not None:
                gnb_entry["target_height_m"] = g.target_height_m
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
            if u.usd_path:
                ue_entry["usd"] = u.usd_path
            if u.target_height_m is not None:
                ue_entry["target_height_m"] = u.target_height_m
            if u.waypoints_json:
                ue_entry["waypoints"] = u.waypoints_json
            config["ues"].append(ue_entry)

        # Obstacles
        obstacles_qs = ObstacleObject.objects.filter(**building_filters) if building_filters else ObstacleObject.objects.all()
        for o in obstacles_qs:
            obstacle_entry = {
                "name": o.name,
                "position": [o.pos_x, o.pos_y, o.pos_z],
                "size": [o.size_x, o.size_y, o.size_z],
                "color": [o.color_r, o.color_g, o.color_b],
            }
            if o.material:
                obstacle_entry["material"] = o.material
            if o.usd_path:
                obstacle_entry["usd"] = o.usd_path
            if o.scale_x != 1.0 or o.scale_y != 1.0 or o.scale_z != 1.0:
                obstacle_entry["scale"] = [o.scale_x, o.scale_y, o.scale_z]
            config["obstacles"].append(obstacle_entry)

        return config
