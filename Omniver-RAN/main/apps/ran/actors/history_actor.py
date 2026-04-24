from __future__ import annotations

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import PositionHistory, SignalHistory
from main.apps.ran.serializers.history_serializers import (
    HistoryQueryWriteSerializer,
    PositionHistoryReadSerializer,
    SignalHistoryReadSerializer,
)
from main.apps.ran.services.business.sqldb_operations import SqlDbBusinessService
from main.apps.ran.services.common.validation_service import ValidationService
from main.utils.response import error_response, success_response


class PositionHistoryReader:
    @staticmethod
    @actor
    def read(request):
        data, err = parse_body(request)
        if err is not None:
            return err
        s = HistoryQueryWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)
        v = s.validated_data
        try:
            t0 = ValidationService.parse_since(v.get("since"))
        except ValueError as e:
            return error_response(str(e), status=422)
        rows = SqlDbBusinessService.list_entities(
            PositionHistory,
            filters={"entity_name": v["ue_name"], "position_ts__gte": t0},
            order_by=["position_ts"],
        )
        return success_response([PositionHistoryReadSerializer.to_representation(r) for r in rows])


class SignalHistoryReader:
    @staticmethod
    @actor
    def read(request):
        data, err = parse_body(request)
        if err is not None:
            return err
        s = HistoryQueryWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)
        v = s.validated_data
        try:
            t0 = ValidationService.parse_since(v.get("since"))
        except ValueError as e:
            return error_response(str(e), status=422)
        rows = SqlDbBusinessService.list_entities(
            SignalHistory,
            filters={"ue_name": v["ue_name"], "signal_ts__gte": t0},
            order_by=["signal_ts"],
        )
        return success_response([SignalHistoryReadSerializer.to_representation(r) for r in rows])
