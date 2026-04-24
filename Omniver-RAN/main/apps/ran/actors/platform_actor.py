from __future__ import annotations

from django.db import transaction

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import PlatformEvent
from main.apps.ran.serializers.platform_serializers import PlatformReportWriteSerializer
from main.apps.ran.services.business.sqldb_operations import SqlDbBusinessService
from main.apps.ran.services.common.uuid_service import UUIDService
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response

log = get_logger(__name__)


class PlatformReporter:
    """Stub — 架構圖「將數值還傳給平台」。目前落 DB + log。"""

    @staticmethod
    @actor
    @transaction.atomic
    def create(request):
        data, err = parse_body(request)
        if err is not None:
            return err
        s = PlatformReportWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)
        v = s.validated_data

        event_uuid = UUIDService.random_uuid()
        SqlDbBusinessService.create_entity(
            PlatformEvent,
            {"event_uuid": event_uuid, "event": v["event"], "payload_json": v["payload"]},
        )
        log.info("platform.report event=%s payload_keys=%s", v["event"], list(v["payload"].keys()))
        return success_response({"event_uuid": event_uuid}, "logged")
