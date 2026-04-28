"""SimSessionController — 管理模擬 session（create / end）。"""
from __future__ import annotations

from datetime import datetime

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import SimulationSession, SignalHistory, PositionHistory
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response


log = get_logger(__name__)


class SimSessionController:
    """控制模擬 session 的生命週期。"""

    @staticmethod
    @actor
    def create(request):
        """建立新的模擬 session。

        Body:
            {
                "session_uuid": str,
                "scene_id": str,
                "scene_snapshot": dict (optional)
            }

        Returns:
            {session_uuid, scene_id, status, created_at}
        """
        data, error = parse_body(request)
        if error:
            return error

        session_uuid = data.get("session_uuid")
        scene_id = data.get("scene_id")
        scene_snapshot = data.get("scene_snapshot", {})

        if not session_uuid or not scene_id:
            return error_response("Missing session_uuid or scene_id", {}, 400)

        log.info("SimSessionController.create session_uuid=%s scene_id=%s", session_uuid, scene_id)

        try:
            metadata_json = {"created_by": "ran_sim"}
            if scene_snapshot:
                metadata_json["scene_snapshot"] = scene_snapshot

            session = SimulationSession.objects.create(
                session_uuid=session_uuid,
                scene_id=scene_id,
                status="running",
                metadata_json=metadata_json,
            )

            # 清理舊 session：保留最近 10 筆
            sessions = SimulationSession.objects.order_by("created_at")
            if sessions.count() > 10:
                oldest = sessions.first()
                log.info("Deleting oldest session %s to keep max 10", oldest.session_uuid)
                # 級聯刪除關聯的 SignalHistory 和 PositionHistory
                SignalHistory.objects.filter(session_uuid=oldest.session_uuid).delete()
                PositionHistory.objects.filter(session_uuid=oldest.session_uuid).delete()
                oldest.delete()

            return success_response(
                {
                    "session_uuid": session.session_uuid,
                    "scene_id": session.scene_id,
                    "status": session.status,
                    "created_at": session.created_at.isoformat(),
                },
                message="Session created",
                status=201,
            )
        except Exception as e:
            log.exception("Failed to create session")
            return error_response(f"Failed to create session: {e}", {}, 500)

    @staticmethod
    @actor
    def end(request):
        """結束模擬 session。

        Body:
            {
                "session_uuid": str
            }

        Returns:
            {session_uuid, status, ended_at}
        """
        data, error = parse_body(request)
        if error:
            return error

        session_uuid = data.get("session_uuid")
        if not session_uuid:
            return error_response("Missing session_uuid", {}, 400)

        log.info("SimSessionController.end session_uuid=%s", session_uuid)

        try:
            session = SimulationSession.objects.get(session_uuid=session_uuid)
            session.status = "ended"
            session.ended_at = datetime.now()
            session.save()

            return success_response(
                {
                    "session_uuid": session.session_uuid,
                    "status": session.status,
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                },
                message="Session ended",
            )
        except SimulationSession.DoesNotExist:
            return error_response(f"Session {session_uuid} not found", {}, 404)
        except Exception as e:
            log.exception("Failed to end session")
            return error_response(f"Failed to end session: {e}", {}, 500)
