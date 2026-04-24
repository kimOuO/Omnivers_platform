from __future__ import annotations

from django.db import transaction

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import UeConfig
from main.apps.ran.serializers.ue_serializers import (
    UeMoveWriteSerializer,
    UeReadSerializer,
    UeTrajectoryWriteSerializer,
)
from main.apps.ran.services.business.kit_operations import KitBusinessService
from main.apps.ran.services.business.sqldb_operations import SqlDbBusinessService
from main.apps.ran.services.common.timestamp_service import TimestampService
from main.apps.ran.services.common.uuid_service import UUIDService
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response

log = get_logger(__name__)


class UEReader:
    """Read current UE list from Kit and normalize."""

    @staticmethod
    @actor
    def read(request):  # noqa: ARG004
        try:
            raw = KitBusinessService.list_ues()
        except Exception as e:  # noqa: BLE001
            return error_response("Kit unreachable", {"detail": str(e)}, 502)

        items: list[dict] = []
        if isinstance(raw, dict):
            items = [{"name": name, **(payload if isinstance(payload, dict) else {})}
                     for name, payload in raw.items()]
        elif isinstance(raw, list):
            items = raw
        output = [UeReadSerializer.to_representation(x) for x in items]
        return success_response(output)


class UEController:
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
    @transaction.atomic
    def trajectory(request):
        data, err = parse_body(request)
        if err is not None:
            return err
        s = UeTrajectoryWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)
        v = s.validated_data

        # Persist the trajectory intent (upsert into ue_config)
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

        # Push to Kit so the viewport follows immediately
        try:
            KitBusinessService.set_trajectory(v["name"], v["waypoints"], v["speed_mps"], v["loop"])
        except Exception as e:  # noqa: BLE001
            log.error("UEController.trajectory Kit push failed: %s", e)
            return error_response("Kit unreachable", {"detail": str(e)}, 502)

        return success_response({"name": v["name"], "waypoints_count": len(v["waypoints"])}, "queued")
