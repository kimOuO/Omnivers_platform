"""Ingest actors — 外部 (模擬 RAN / Sionna DU) 透過這些 endpoint 寫入資料。"""
from __future__ import annotations

from django.db import transaction

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import BuildingObject, GnbConfig, UeConfig
from main.apps.ran.serializers.ingest_serializers import SignalBatchWriteSerializer
from main.apps.ran.serializers.scene_serializers import SceneInitWriteSerializer
from main.apps.ran.services.business.ingest_operations import IngestBusinessService
from main.apps.ran.services.business.kit_operations import KitBusinessService
from main.apps.ran.services.business.ranpsim_operations import RanpsimBusinessService
from main.apps.ran.services.business.sqldb_operations import SqlDbBusinessService
from main.apps.ran.services.common.timestamp_service import TimestampService
from main.apps.ran.services.common.uuid_service import UUIDService
from main.apps.ran.services.optional.scene_config_generator import SceneConfigGeneratorService
from main.apps.ran.services.optional.translation.payload_translator import PayloadTranslator
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response

log = get_logger(__name__)


class SignalIngestor:
    """POST /api/v0.1/RAN/Ingest/SignalIngestor/create"""

    @staticmethod
    @actor
    def create(request):
        data, err = parse_body(request)
        if err is not None:
            return err
        s = SignalBatchWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)
        v = s.validated_data

        ts = TimestampService.parse_iso(v["ts"]) if v.get("ts") else TimestampService.get_current_timestamp()
        session_uuid = v.get("session_uuid")  # 可選，由 RAN-sim 提供
        result = IngestBusinessService.ingest_signals(v["signals"], ts=ts, session_uuid=session_uuid)
        return success_response(result)


class SceneIngestor:
    """POST /api/v0.1/RAN/Ingest/SceneIngestor/create"""

    @staticmethod
    @actor
    @transaction.atomic
    def create(request):
        data, err = parse_body(request)
        if err is not None:
            return err
        s = SceneInitWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)
        v = s.validated_data

        scene_id = v["scene_id"]

        # Upsert BuildingObject for each building
        for b in v.get("buildings", []):
            name = b.get("name")
            if not name:
                continue
            pos = b.get("position", [0, 0, 0])
            size = b.get("size", [10, 10, 10])
            color = b.get("color", [0.75, 0.75, 0.75])
            building_defaults = {
                "building_uuid": UUIDService.generate_uuid("building", name),
                "scene_id": scene_id,
                "pos_x": float(pos[0]) if len(pos) > 0 else 0,
                "pos_y": float(pos[1]) if len(pos) > 1 else 0,
                "pos_z": float(pos[2]) if len(pos) > 2 else 0,
                "size_x": float(size[0]) if len(size) > 0 else 10,
                "size_y": float(size[1]) if len(size) > 1 else 10,
                "size_z": float(size[2]) if len(size) > 2 else 10,
                "color_r": float(color[0]) if len(color) > 0 else 0.75,
                "color_g": float(color[1]) if len(color) > 1 else 0.75,
                "color_b": float(color[2]) if len(color) > 2 else 0.75,
                "usd_path": b.get("usd_path", b.get("usd", "")),
                "target_height_m": float(b["target_height_m"]) if b.get("target_height_m") else None,
                "material": b.get("material", ""),
            }
            # Only update rotation if explicitly provided in payload — prevents ingest from resetting to [0,0,0]
            rot = b.get("rotation_xyz_deg")
            if rot is not None:
                building_defaults["rot_x"] = float(rot[0]) if len(rot) > 0 else 0
                building_defaults["rot_y"] = float(rot[1]) if len(rot) > 1 else 0
                building_defaults["rot_z"] = float(rot[2]) if len(rot) > 2 else 0
            SqlDbBusinessService.upsert_entity(
                BuildingObject,
                lookup={"name": name},
                defaults=building_defaults,
            )

        # upsert gNB configs with new position/color fields
        for g in v.get("gnbs", []):
            name = g.get("name")
            if not name:
                continue
            freq_mhz = (float(g["frequency_ghz"]) * 1000.0) if g.get("frequency_ghz") else float(g.get("freq_mhz", 0))
            bw_hz = (float(g["bandwidth_mhz"]) * 1_000_000.0) if g.get("bandwidth_mhz") else float(g.get("bw_hz", 0))
            pos = g.get("position", [0, 0, 0])
            color = g.get("color", [1.0, 1.0, 1.0])
            SqlDbBusinessService.upsert_entity(
                GnbConfig,
                lookup={"name": name},
                defaults={
                    "gnb_uuid": UUIDService.generate_uuid("gnb", name),
                    "freq_mhz": freq_mhz,
                    "power_dbm": float(g.get("power_dbm", 0)),
                    "bw_hz": bw_hz,
                    "active": True,
                    "pos_x": float(pos[0]) if len(pos) > 0 else 0,
                    "pos_y": float(pos[1]) if len(pos) > 1 else 0,
                    "pos_z": float(pos[2]) if len(pos) > 2 else 0,
                    "color_r": float(color[0]) if len(color) > 0 else 1.0,
                    "color_g": float(color[1]) if len(color) > 1 else 1.0,
                    "color_b": float(color[2]) if len(color) > 2 else 1.0,
                    "target_height_m": float(g["target_height_m"]) if g.get("target_height_m") else None,
                },
            )

        # Upsert UeConfig for each UE
        for u in v.get("ues", []):
            name = u.get("name")
            if not name:
                continue
            pos = u.get("position", [0, 0, 0])
            color = u.get("color", [0.5, 0.5, 0.5])
            waypoints = u.get("waypoints", [])
            SqlDbBusinessService.upsert_entity(
                UeConfig,
                lookup={"name": name},
                defaults={
                    "ue_uuid": UUIDService.generate_uuid("ue", name),
                    "waypoints_json": waypoints,
                    "speed_mps": float(u.get("speed_mps", 1.0)),
                    "loop": True,
                    "pos_x": float(pos[0]) if len(pos) > 0 else 0,
                    "pos_y": float(pos[1]) if len(pos) > 1 else 0,
                    "pos_z": float(pos[2]) if len(pos) > 2 else 0,
                    "color_r": float(color[0]) if len(color) > 0 else 0.5,
                    "color_g": float(color[1]) if len(color) > 1 else 0.5,
                    "color_b": float(color[2]) if len(color) > 2 else 0.5,
                    "usd_path": u.get("usd", ""),
                    "target_height_m": float(u["target_height_m"]) if u.get("target_height_m") else None,
                },
            )

        # Push scene to Kit (generate config from DB and send to Kit)
        config_for_push = dict(v)
        transaction.on_commit(
            lambda: _push_scene_to_kit_and_ranpsim(scene_id, config_for_push)
        )

        return success_response({"scene_id": scene_id}, "stored")


def _push_scene_to_kit_and_ranpsim(scene_id: str, config_json: dict) -> None:
    """Push scene config to both Kit (for visualization) and RAN-sim (for calculation)."""
    # 1. Generate config from DB models
    try:
        config_from_db = SceneConfigGeneratorService.generate(scene_id=scene_id)
        log.info("SceneIngestor: generated config from DB for scene_id=%s", scene_id)
    except Exception as e:  # noqa: BLE001
        log.warning("SceneIngestor: failed to generate config from DB (scene_id=%s): %s, using snapshot", scene_id, e)
        config_from_db = config_json

    # 2. Push to Kit (visualization)
    try:
        KitBusinessService.push_scene_config(config_from_db)
        KitBusinessService.build_scene()
        log.info("SceneIngestor: pushed config to Kit (scene_id=%s)", scene_id)
    except Exception as e:  # noqa: BLE001
        log.warning("SceneIngestor: Kit push_scene_config failed (scene_id=%s): %s", scene_id, e)

    # 3. Push to RAN-sim (backward compatibility)
    try:
        payload = PayloadTranslator.snapshot_to_ranpsim_push_scene(scene_id, config_json)
        RanpsimBusinessService.push_scene(
            scene_id=payload["scene_id"],
            gnbs=payload["gnbs"],
            override_mode=payload["override_mode"],
            buildings=payload.get("geometry_source", {}).get("buildings"),
            ues=payload.get("ues"),
        )
        log.info("SceneIngestor: push_scene to RAN-sim OK (scene_id=%s)", scene_id)
    except Exception as e:  # noqa: BLE001
        log.warning("SceneIngestor: ranp-sim push_scene failed (scene_id=%s): %s",
                    scene_id, e)
