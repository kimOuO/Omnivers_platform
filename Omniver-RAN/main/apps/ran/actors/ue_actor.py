from __future__ import annotations

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import UeConfig
from main.apps.ran.serializers.ue_serializers import (
    UeMoveWriteSerializer,
    UeReadSerializer,
    UeTrajectoryWriteSerializer,
    UeWriteSerializer,
)
from main.apps.ran.services.business.kit_operations import KitBusinessService
from main.apps.ran.services.business.sqldb_operations import SqlDbBusinessService
from main.apps.ran.services.common.timestamp_service import TimestampService
from main.apps.ran.services.common.uuid_service import UUIDService
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response

log = get_logger(__name__)


class UEReader:
    """Read UE list from database."""

    @staticmethod
    @actor
    def read(request):  # noqa: ARG004
        try:
            ues = SqlDbBusinessService.list_entities(UeConfig)
            output = [UeReadSerializer.to_representation(u) for u in ues]
            return success_response(output)
        except Exception as e:  # noqa: BLE001
            return error_response("Failed to read UEs from database", {"detail": str(e)}, 500)


class UEController:
    @staticmethod
    @actor
    def create(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        s = UeWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)

        v = s.validated_data
        ue_uuid = UUIDService.generate_uuid("ue", v["name"])
        ts = TimestampService.get_current_timestamp()

        entity_data = {
            "ue_uuid": ue_uuid,
            "ue_created_at": ts,
            "ue_updated_at": ts,
            **v,
        }

        ue = SqlDbBusinessService.create_entity(UeConfig, entity_data)
        output = UeReadSerializer.to_representation(ue)
        return success_response(output, "UE created", 201)

    @staticmethod
    @actor
    def delete(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        name = data.get("name")
        if not name or not isinstance(name, str):
            return error_response("Validation failed", {"name": "required (str)"}, 400)

        cfg = SqlDbBusinessService.find_entity(UeConfig, name=name)
        if cfg is None:
            return error_response(f"UE '{name}' not found", status=404)

        SqlDbBusinessService.delete_entity(cfg)
        return success_response({"name": name}, "UE deleted")

    @staticmethod
    @actor
    def update(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        name = data.get("name")
        if not name or not isinstance(name, str):
            return error_response("Validation failed", {"name": "required (str)"}, 400)

        cfg = SqlDbBusinessService.find_entity(UeConfig, name=name)
        if cfg is None:
            return error_response(f"UE '{name}' not found", status=404)

        updates: dict = {"ue_updated_at": TimestampService.get_current_timestamp()}
        if "position" in data:
            pos = data["position"]
            updates["pos_x"] = float(pos[0])
            updates["pos_y"] = float(pos[1])
            updates["pos_z"] = float(pos[2])
        if "speed_mps" in data:
            updates["speed_mps"] = float(data["speed_mps"])
        if "waypoints" in data:
            updates["waypoints_json"] = data["waypoints"]

        SqlDbBusinessService.update_entity(cfg, updates)
        cfg.refresh_from_db()
        output = UeReadSerializer.to_representation(cfg)
        return success_response(output, "UE updated")

    @staticmethod
    @actor
    def move(request):
        data, err = parse_body(request)
        if err is not None:
            return err
        s = UeMoveWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)
        v = s.validated_data
        try:
            KitBusinessService.move_ue(v["name"], v["x"], v["y"], v["z"])
        except Exception as e:  # noqa: BLE001
            return error_response("Kit unreachable", {"detail": str(e)}, 502)
        return success_response({"name": v["name"], "x": v["x"], "y": v["y"], "z": v["z"]}, "queued")

    @staticmethod
    @actor
    def trajectory(request):
        data, err = parse_body(request)
        if err is not None:
            return err
        s = UeTrajectoryWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)
        v = s.validated_data

        timestamp = TimestampService.get_current_timestamp()
        ue_uuid = UUIDService.generate_uuid("ue", v["name"])
        SqlDbBusinessService.upsert_entity(
            UeConfig,
            lookup={"name": v["name"]},
            defaults={
                "ue_uuid": ue_uuid,
                "waypoints_json": v["waypoints"],
                "speed_mps": v["speed_mps"],
                "loop": v["loop"],
                "ue_updated_at": timestamp,
            },
        )

        try:
            KitBusinessService.set_trajectory(v["name"], v["waypoints"], v["speed_mps"], v["loop"])
        except Exception as e:  # noqa: BLE001
            log.error("UEController.trajectory Kit push failed: %s", e)
            return error_response("Kit unreachable", {"detail": str(e)}, 502)

        return success_response({"name": v["name"], "waypoints_count": len(v["waypoints"])}, "queued")

    @staticmethod
    @actor
    def batch_move(request):
        """批次移動多個 UE（用於 Playback 3D 重播）。

        Body: { "ues": [{"name": "ue1", "x": 10.0, "y": 0.0, "z": 5.0}, ...] }
        """
        data, err = parse_body(request)
        if err is not None:
            return err

        ues = data.get("ues")
        if not isinstance(ues, list):
            return error_response("Validation failed", {"ues": "required (list)"}, 400)

        moved = []
        for ue in ues:
            name = ue.get("name")
            if not name:
                continue
            try:
                KitBusinessService.move_ue(
                    name,
                    float(ue.get("x", 0.0)),
                    float(ue.get("y", 0.0)),
                    float(ue.get("z", 0.0)),
                )
                moved.append(name)
            except Exception as e:  # noqa: BLE001
                log.warning("batch_move: Kit move failed for %s: %s", name, e)

        return success_response({"moved": moved, "count": len(moved)})
