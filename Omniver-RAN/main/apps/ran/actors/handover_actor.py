"""HandoverIngestor / HandoverReader — 收 RAN-sim CU push 的 HO 事件,
讓 playback 把 handover 切回對應 frame_ts。
"""
from __future__ import annotations

from datetime import datetime

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import HandoverHistory, SimulationSession
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response


log = get_logger(__name__)


def _parse_ts(raw):
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        # 支援 ISO8601 (帶或不帶 timezone) 與 RAN-sim 的 .isoformat()。
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


class HandoverIngestor:
    """CU `handover_executor.execute_f1_handover` 落地後 fire-and-forget 推一份過來。"""

    @staticmethod
    @actor
    def create(request):
        """Body:
            {
                "ho_uuid": str,
                "ue_name": str,
                "source_cell": str,
                "target_cell": str,
                "trigger": str,
                "status": str,
                "event_ts": ISO8601 (optional, default now),
                "session_uuid": str (optional, fallback latest running)
            }
        """
        data, error = parse_body(request)
        if error:
            return error

        ho_uuid = data.get("ho_uuid")
        ue_name = data.get("ue_name") or data.get("ue_id")
        source_cell = data.get("source_cell") or ""
        target_cell = data.get("target_cell") or ""

        if not ho_uuid or not ue_name or not target_cell:
            return error_response(
                "Missing ho_uuid / ue_name / target_cell", {}, 400
            )

        event_ts = _parse_ts(data.get("event_ts")) or datetime.now()
        session_uuid = data.get("session_uuid")
        if not session_uuid:
            session_uuid = (
                SimulationSession.objects
                .filter(status="running")
                .order_by("-created_at")
                .values_list("session_uuid", flat=True)
                .first()
            )

        defaults = {
            "session_uuid": session_uuid,
            "ue_name": ue_name,
            "source_cell": source_cell,
            "target_cell": target_cell,
            "trigger": data.get("trigger") or "A3_TTT",
            "status": data.get("status") or "SUCC",
            "event_ts": event_ts,
        }
        try:
            obj, created = HandoverHistory.objects.update_or_create(
                ho_uuid=ho_uuid, defaults=defaults,
            )
            log.info(
                "HandoverIngestor.create ho_uuid=%s ue=%s %s->%s session=%s %s",
                ho_uuid[:8], ue_name, source_cell, target_cell, session_uuid,
                "created" if created else "updated",
            )
            return success_response(
                {"ho_uuid": ho_uuid, "created": created},
                message="HO recorded",
                status=201 if created else 200,
            )
        except Exception as e:
            log.exception("Failed to ingest handover event")
            return error_response(f"Failed to ingest handover: {e}", {}, 500)


class HandoverReader:
    @staticmethod
    @actor
    def read(request):
        """Body:
            {
                "session_uuid": str
            }

        Returns:
            { handovers: [{ho_uuid, ue_name, source_cell, target_cell,
                            trigger, status, event_ts}], count: N }
        """
        data, error = parse_body(request)
        if error:
            return error

        session_uuid = data.get("session_uuid")
        if not session_uuid:
            return error_response("Missing session_uuid", {}, 400)

        qs = HandoverHistory.objects.filter(session_uuid=session_uuid).order_by("event_ts")
        rows = [
            {
                "ho_uuid": h.ho_uuid,
                "ue_name": h.ue_name,
                "source_cell": h.source_cell,
                "target_cell": h.target_cell,
                "trigger": h.trigger,
                "status": h.status,
                "event_ts": h.event_ts.isoformat() if h.event_ts else None,
            }
            for h in qs
        ]
        return success_response({"handovers": rows, "count": len(rows)})
