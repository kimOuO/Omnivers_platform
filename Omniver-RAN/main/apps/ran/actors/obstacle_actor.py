from __future__ import annotations

from django.db import transaction

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import ObstacleObject
from main.apps.ran.serializers.obstacle_serializers import (
    ObstacleReadSerializer,
    ObstacleWriteSerializer,
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


class ObstacleController:
    @staticmethod
    @actor
    @transaction.atomic
    def create(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        s = ObstacleWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)

        v = s.validated_data
        obstacle_uuid = UUIDService.generate_uuid("obstacle", v["name"])
        ts = TimestampService.get_current_timestamp()

        entity_data = {
            "obstacle_uuid": obstacle_uuid,
            "obstacle_created_at": ts,
            "obstacle_updated_at": ts,
            **v,
        }

        obstacle = SqlDbBusinessService.create_entity(ObstacleObject, entity_data)
        output = ObstacleReadSerializer.to_representation(obstacle)

        transaction.on_commit(lambda: _rebuild_kit_scene())

        return success_response(output, "Obstacle created", 201)

    @staticmethod
    @actor
    def read(request):  # noqa: ARG004
        try:
            obstacles = SqlDbBusinessService.list_entities(ObstacleObject)
            output = [ObstacleReadSerializer.to_representation(o) for o in obstacles]
            return success_response(output)
        except Exception as e:  # noqa: BLE001
            return error_response("Failed to read obstacles", {"detail": str(e)}, 500)

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

        obstacle = SqlDbBusinessService.find_entity(ObstacleObject, name=name)
        if obstacle is None:
            return error_response(f"Obstacle '{name}' not found", status=404)

        s = ObstacleWriteSerializer(data=data)
        # 更新時只允許修改 USD 規範的屬性（position, size, color, scale, material, usd_path）
        v = s._validate_update(data)
        if not v:
            return error_response("No editable USD fields provided (allowed: position, size, color, scale, material, usd_path)", status=400)

        v["obstacle_updated_at"] = TimestampService.get_current_timestamp()

        updated = SqlDbBusinessService.update_entity(obstacle, v)
        output = ObstacleReadSerializer.to_representation(updated)

        transaction.on_commit(lambda: _rebuild_kit_scene())

        return success_response(output, "Obstacle updated", 200)

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

        obstacle = SqlDbBusinessService.find_entity(ObstacleObject, name=name)
        if obstacle is None:
            return error_response(f"Obstacle '{name}' not found", status=404)

        SqlDbBusinessService.delete_entity(obstacle)

        transaction.on_commit(lambda: _rebuild_kit_scene())

        return success_response(None, "Obstacle deleted", 204)
