from __future__ import annotations

from django.db import transaction

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import BuildingObject
from main.apps.ran.serializers.building_serializers import (
    BuildingReadSerializer,
    BuildingWriteSerializer,
)
from main.apps.ran.services.business.kit_operations import KitBusinessService
from main.apps.ran.services.business.sqldb_operations import SqlDbBusinessService
from main.apps.ran.services.common.uuid_service import UUIDService
from main.apps.ran.services.common.timestamp_service import TimestampService
from main.apps.ran.services.optional.scene_config_generator import SceneConfigGeneratorService
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response

log = get_logger(__name__)


def _rebuild_kit_scene() -> None:
    """Generate config from DB and push to Kit."""
    try:
        config = SceneConfigGeneratorService.generate()
        KitBusinessService.push_scene_config(config)
        KitBusinessService.build_scene()
    except Exception as e:  # noqa: BLE001
        log.error("Failed to rebuild Kit scene: %s", e)


class BuildingController:
    @staticmethod
    @actor
    @transaction.atomic
    def create(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        s = BuildingWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)

        v = s.validated_data
        building_uuid = UUIDService.generate_uuid("building", v["name"])
        ts = TimestampService.get_current_timestamp()

        entity_data = {
            "building_uuid": building_uuid,
            "building_created_at": ts,
            "building_updated_at": ts,
            **v,
        }

        building = SqlDbBusinessService.create_entity(BuildingObject, entity_data)
        output = BuildingReadSerializer.to_representation(building)

        transaction.on_commit(lambda: _rebuild_kit_scene())

        return success_response(output, "Building created", 201)

    @staticmethod
    @actor
    def read(request):  # noqa: ARG004
        try:
            buildings = SqlDbBusinessService.list_entities(BuildingObject)
            output = [BuildingReadSerializer.to_representation(b) for b in buildings]
            return success_response(output)
        except Exception as e:  # noqa: BLE001
            return error_response("Failed to read buildings", {"detail": str(e)}, 500)

    @staticmethod
    @actor
    @transaction.atomic
    def update(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        name = data.get("name")
        if not name or not isinstance(name, str):
            return error_response("Validation failed", {"name": "required (str)"}, 400)

        building = SqlDbBusinessService.find_entity(BuildingObject, name=name)
        if building is None:
            return error_response(f"Building '{name}' not found", status=404)

        s = BuildingWriteSerializer(data=data)
        # 更新時只允許修改 USD 規範的屬性（position, size, color, rotation, material, usd_path, target_height_m）
        v = s._validate_update(data)
        if not v:
            return error_response("No editable USD fields provided (allowed: position, size, color, rotation_xyz_deg, material, usd_path, target_height_m)", status=400)

        v["building_updated_at"] = TimestampService.get_current_timestamp()

        updated = SqlDbBusinessService.update_entity(building, v)
        output = BuildingReadSerializer.to_representation(updated)

        transaction.on_commit(lambda: _rebuild_kit_scene())

        return success_response(output, "Building updated", 200)

    @staticmethod
    @actor
    @transaction.atomic
    def delete(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        name = data.get("name")
        if not name or not isinstance(name, str):
            return error_response("Validation failed", {"name": "required (str)"}, 400)

        building = SqlDbBusinessService.find_entity(BuildingObject, name=name)
        if building is None:
            return error_response(f"Building '{name}' not found", status=404)

        SqlDbBusinessService.delete_entity(building)

        transaction.on_commit(lambda: _rebuild_kit_scene())

        return success_response(None, "Building deleted", 204)
