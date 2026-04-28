from __future__ import annotations

from django.db import transaction

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import UsdAsset
from main.apps.ran.serializers.asset_serializers import (
    UsdAssetReadSerializer,
    UsdAssetWriteSerializer,
    UsdAssetUpdateSerializer,
)
from main.apps.ran.services.business.sqldb_operations import SqlDbBusinessService
from main.apps.ran.services.common.uuid_service import UUIDService
from main.apps.ran.services.common.timestamp_service import TimestampService
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response

log = get_logger(__name__)


class UsdAssetReader:
    @staticmethod
    @actor
    def list(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        try:
            filters = {"active": True}
            object_type = data.get("object_type") if data else None
            if object_type:
                filters["object_type"] = object_type
            assets = SqlDbBusinessService.list_entities(UsdAsset, filters=filters)
            output = [UsdAssetReadSerializer.to_representation(a) for a in assets]
            return success_response(output)
        except Exception as e:  # noqa: BLE001
            return error_response("Failed to list assets", {"detail": str(e)}, 500)


class UsdAssetController:
    @staticmethod
    @actor
    @transaction.atomic
    def create(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        s = UsdAssetWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)

        v = s.validated_data
        asset_uuid = UUIDService.generate_uuid("asset", v["preset_id"])
        ts = TimestampService.get_current_timestamp()

        entity_data = {
            "asset_uuid": asset_uuid,
            "preset_id": v["preset_id"],
            "object_type": v["object_type"],
            "label": v["label"],
            "description": v.get("description", ""),
            "usd_path": v["usd_path"],
            "default_size": v.get("default_size"),
            "default_color": v.get("default_color"),
            "default_scale": v.get("default_scale"),
            "active": True,
        }

        asset = SqlDbBusinessService.create_entity(UsdAsset, entity_data)
        output = UsdAssetReadSerializer.to_representation(asset)
        return success_response(output, "Asset created", 201)

    @staticmethod
    @actor
    @transaction.atomic
    def update(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        preset_id = data.get("preset_id")
        if not preset_id or not isinstance(preset_id, str):
            return error_response("Validation failed", {"preset_id": "required (str)"}, 400)

        asset = SqlDbBusinessService.find_entity(UsdAsset, preset_id=preset_id)
        if asset is None:
            return error_response(f"Asset '{preset_id}' not found", status=404)

        s = UsdAssetUpdateSerializer(data=data)
        v = s._validate_update(data)
        if not v:
            return error_response(
                "No editable fields provided (allowed: label, description, default_size, default_color, default_scale, active)",
                status=400,
            )

        v["asset_updated_at"] = TimestampService.get_current_timestamp()
        updated = SqlDbBusinessService.update_entity(asset, v)
        output = UsdAssetReadSerializer.to_representation(updated)
        return success_response(output, "Asset updated", 200)

    @staticmethod
    @actor
    @transaction.atomic
    def delete(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        preset_id = data.get("preset_id")
        if not preset_id or not isinstance(preset_id, str):
            return error_response("Validation failed", {"preset_id": "required (str)"}, 400)

        asset = SqlDbBusinessService.find_entity(UsdAsset, preset_id=preset_id)
        if asset is None:
            return error_response(f"Asset '{preset_id}' not found", status=404)

        asset.active = False
        asset.asset_updated_at = TimestampService.get_current_timestamp()
        SqlDbBusinessService.update_entity(asset, {"active": False, "asset_updated_at": asset.asset_updated_at})
        return success_response(None, "Asset deactivated", 204)
