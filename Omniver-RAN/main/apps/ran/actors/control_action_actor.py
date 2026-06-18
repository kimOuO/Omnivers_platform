"""ControlActionIngestor / ControlActionReader — 收 RAN-sim CU push 的 E2 Control Request,
讓 playback timeline 看到 xApp 下了什麼指令。
"""
from __future__ import annotations

from datetime import datetime, timezone

from django.http import JsonResponse

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


# ════════════════════════════════════════════════════════════════════
# RcObservationReader — 對外「拉 RC 指令資訊」API(規範版)
#   GET-like POST,沿用 ControlAction(CU e2_control_actor push 的結構化 RC),
#   不另 tail CU log。輸入 action_type/since/until/limit,輸出 RcCommandObservation[]。
# ════════════════════════════════════════════════════════════════════

# action_type ↔ (style, action) / label 對應
_ACTION_TYPE_BY_LABEL = {
    "PRB_QUOTA": "rc_control_quota",
    "HANDOVER": "rc_control_ho",
}
_LABELS_BY_ACTION_TYPE = {
    "rc_control_quota": ["PRB_QUOTA"],
    "rc_control_ho": ["HANDOVER"],
}
_VALID_ACTION_TYPES = {"rc_control_quota", "rc_control_ho", "rc_control_unsupported"}
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _iso_z(dt) -> str | None:
    """ISO 8601 並以 Z 結尾(對齊規範範例;naive datetime 視為 UTC)。"""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _action_type_of(a: "ControlAction") -> str:
    return _ACTION_TYPE_BY_LABEL.get((a.action_label or "").upper(), "rc_control_unsupported")


def _params_of(a: "ControlAction", action_type: str) -> dict:
    p = a.payload_json or {}
    if action_type == "rc_control_quota":
        return {
            "min": p.get("min_prb", 0),
            "max": p.get("max_prb", 100),
            "dedicated": p.get("dedicated_prb", 0),
        }
    if action_type == "rc_control_ho":
        # rrc_ue_id:優先 payload,退而用 ue_name(CU push 帶的 ue_id)
        return {"rrc_ue_id": p.get("rrc_ue_id", a.ue_name)}
    return dict(p)


def _raw_of(a: "ControlAction", action_type: str, params: dict) -> str:
    # 若 CU 之後有把實際 log 行帶進 payload_json["raw"],優先用它;否則由欄位重建。
    raw = (a.payload_json or {}).get("raw")
    if raw:
        return str(raw)
    s, act = a.control_style, a.control_action_id
    if action_type == "rc_control_quota":
        return (f"[E2 AGENT][RC] Style {s}/Action {act}: "
                f"min={params['min']}% max={params['max']}% dedicated={params['dedicated']}%")
    if action_type == "rc_control_ho":
        return f"[E2 AGENT][RC] Style {s}/Action {act}: handover rrc_ue_id={params.get('rrc_ue_id')}"
    return f"[E2 AGENT][RC] Style {s}/Action {act}: {a.action_label}"


def _to_observation(a: "ControlAction") -> dict:
    at = _action_type_of(a)
    params = _params_of(a, at)
    return {
        "uuid": (a.payload_json or {}).get("obs_uuid") or f"ca{a.id}",
        "observed_at": _iso_z(a.action_ts),
        "action_type": at,
        "e2_style": str(a.control_style),
        "e2_action": str(a.control_action_id),
        "target": "cu",
        "params": params,
        "evidence": "cu_log",
        "raw": _raw_of(a, at, params),
    }


class RcObservationReader:
    @staticmethod
    @actor
    def read(request):
        """對外拉 RC 指令觀察。

        Body: { action_type?, since?(ISO8601), until?(ISO8601), limit?(<=200, def 50) }
        回傳外層 {status, data, message, timestamp};data 見規範。
        """
        data, error = parse_body(request)
        if error:
            return error

        action_type = data.get("action_type")
        if action_type is not None and action_type not in _VALID_ACTION_TYPES:
            return JsonResponse({
                "status": "error",
                "data": None,
                "message": f"invalid action_type: {action_type}",
                "timestamp": _now_iso(),
            }, status=400)

        since = _parse_ts(data.get("since"))
        until = _parse_ts(data.get("until"))
        try:
            limit = int(data.get("limit", _DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = _DEFAULT_LIMIT
        limit = max(1, min(limit, _MAX_LIMIT))

        qs = ControlAction.objects.all()
        if since is not None:
            qs = qs.filter(action_ts__gte=since)
        if until is not None:
            qs = qs.filter(action_ts__lte=until)
        if action_type in _LABELS_BY_ACTION_TYPE:
            qs = qs.filter(action_label__in=_LABELS_BY_ACTION_TYPE[action_type])
        elif action_type == "rc_control_unsupported":
            qs = qs.exclude(action_label__in=["PRB_QUOTA", "HANDOVER"])

        qs = qs.order_by("action_ts")
        # 多抓 1 筆判斷 has_more(同條件下是否被 limit 截斷)
        rows = list(qs[: limit + 1])
        has_more = len(rows) > limit
        rows = rows[:limit]

        items = [_to_observation(a) for a in rows]
        latest = items[-1]["observed_at"] if items else None

        return JsonResponse({
            "status": "ok",
            "data": {
                "items": items,
                "count": len(items),
                "latest_observed_at": latest,
                "has_more": has_more,
            },
            "message": None,
            "timestamp": _now_iso(),
        }, status=200)
