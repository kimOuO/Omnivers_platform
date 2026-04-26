"""Ingest actors — 外部 (模擬 RAN / Sionna DU) 透過這些 endpoint 寫入資料。"""
from __future__ import annotations

from django.db import transaction

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import GnbConfig, SceneSnapshot
from main.apps.ran.serializers.ingest_serializers import SignalBatchWriteSerializer
from main.apps.ran.serializers.scene_serializers import SceneInitWriteSerializer
from main.apps.ran.services.business.ingest_operations import IngestBusinessService
from main.apps.ran.services.business.ranpsim_operations import RanpsimBusinessService
from main.apps.ran.services.business.sqldb_operations import SqlDbBusinessService
from main.apps.ran.services.common.timestamp_service import TimestampService
from main.apps.ran.services.common.uuid_service import UUIDService
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

        timestamp = TimestampService.get_current_timestamp()
        scene_uuid = UUIDService.generate_uuid("scene", f"{v['scene_id']}:{timestamp.isoformat()}")

        SqlDbBusinessService.create_entity(
            SceneSnapshot,
            {
                "scene_uuid": scene_uuid,
                "scene_id": v["scene_id"],
                "config_json": v,
            },
        )

        # upsert gNB configs
        for g in v["gnbs"]:
            name = g.get("name")
            if not name:
                continue
            freq_mhz = (float(g["frequency_ghz"]) * 1000.0) if g.get("frequency_ghz") else float(g.get("freq_mhz", 0))
            bw_hz = (float(g["bandwidth_mhz"]) * 1_000_000.0) if g.get("bandwidth_mhz") else float(g.get("bw_hz", 0))
            SqlDbBusinessService.upsert_entity(
                GnbConfig,
                lookup={"name": name},
                defaults={
                    "gnb_uuid": UUIDService.generate_uuid("gnb", name),
                    "freq_mhz": freq_mhz,
                    "power_dbm": float(g.get("power_dbm", 0)),
                    "bw_hz": bw_hz,
                    "active": True,
                },
            )

        # Direct push to ranp-sim (full override) — 等 DB commit 後再打，
        # 失敗不回滾 scene 寫入（Sionna 可以晚點 reload）。
        scene_id = v["scene_id"]
        config_for_push = dict(v)
        transaction.on_commit(
            lambda: _push_scene_to_ranpsim(scene_id, config_for_push)
        )

        return success_response({"scene_uuid": scene_uuid, "scene_id": v["scene_id"]}, "stored")


def _push_scene_to_ranpsim(scene_id: str, config_json: dict) -> None:
    try:
        payload = PayloadTranslator.snapshot_to_ranpsim_push_scene(scene_id, config_json)
        RanpsimBusinessService.push_scene(
            scene_id=payload["scene_id"],
            gnbs=payload["gnbs"],
            override_mode=payload["override_mode"],
            buildings=payload.get("geometry_source", {}).get("buildings"),
            ues=payload.get("ues"),
        )
        log.info("SceneIngestor: push_scene OK (scene_id=%s)", scene_id)
    except Exception as e:  # noqa: BLE001
        log.warning("SceneIngestor: ranp-sim push_scene failed (scene_id=%s): %s",
                    scene_id, e)
