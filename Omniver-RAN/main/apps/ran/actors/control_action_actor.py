"""ControlActionIngestor / ControlActionReader — 收 RAN-sim CU push 的 E2 Control Request,
讓 playback timeline 看到 xApp 下了什麼指令。
"""
from __future__ import annotations

from datetime import datetime

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import ControlAction, SimulationSession
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response


log = get_logger(__name__)


def _parse_ts(raw):
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


class ControlActionIngestor:
    @staticmethod
    @actor
    def create(request):
        """Body:
            {
                "control_style": int,
                "control_action_id": int,
                "action_label": str,
                "ric_req_id": dict,
                "ue_name": str | null,
                "cell_id": str | null,
                "payload_json": dict,
                "outcome": str,
                "error": str | null,
                "action_ts": ISO8601 (optional),
                "session_uuid": str (optional, fallback latest running)
            }
        """
        data, error = parse_body(request)
        if error:
            return error

        style = data.get("control_style")
        action_id = data.get("control_action_id")
        if style is None or action_id is None:
            return error_response("Missing control_style / control_action_id", {}, 400)

        action_ts = _parse_ts(data.get("action_ts")) or datetime.now()
        session_uuid = data.get("session_uuid")
        if not session_uuid:
            session_uuid = (
                SimulationSession.objects
                .filter(status="running")
                .order_by("-created_at")
                .values_list("session_uuid", flat=True)
                .first()
            )

        try:
            obj = ControlAction.objects.create(
                session_uuid=session_uuid,
                ric_req_id=data.get("ric_req_id") or {},
                control_style=int(style),
                control_action_id=int(action_id),
                action_label=str(data.get("action_label") or "")[:64],
                ue_name=data.get("ue_name"),
                cell_id=data.get("cell_id"),
                payload_json=data.get("payload_json") or {},
                outcome=str(data.get("outcome") or "OK")[:64],
                error=data.get("error"),
                action_ts=action_ts,
            )
            log.info(
                "ControlActionIngestor.create style=%s action=%s label=%s ue=%s cell=%s session=%s",
                style, action_id, obj.action_label, obj.ue_name, obj.cell_id, session_uuid,
            )
            return success_response(
                {"id": obj.id}, message="Control action recorded", status=201,
            )
        except Exception as e:
            log.exception("Failed to ingest control action")
            return error_response(f"Failed to ingest control action: {e}", {}, 500)


class ControlActionReader:
    @staticmethod
    @actor
    def read(request):
        """Body: { "session_uuid": str }"""
        data, error = parse_body(request)
        if error:
            return error
        session_uuid = data.get("session_uuid")
        if not session_uuid:
            return error_response("Missing session_uuid", {}, 400)

        qs = ControlAction.objects.filter(session_uuid=session_uuid).order_by("action_ts")
        rows = [
            {
                "id": a.id,
                "ric_req_id": a.ric_req_id,
                "control_style": a.control_style,
                "control_action_id": a.control_action_id,
                "action_label": a.action_label,
                "ue_name": a.ue_name,
                "cell_id": a.cell_id,
                "payload_json": a.payload_json,
                "outcome": a.outcome,
                "error": a.error,
                "action_ts": a.action_ts.isoformat() if a.action_ts else None,
            }
            for a in qs
        ]
        return success_response({"control_actions": rows, "count": len(rows)})
