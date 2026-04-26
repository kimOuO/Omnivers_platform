"""PlaybackController — 回放功能（list / read）。"""
from __future__ import annotations

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import SimulationSession, PositionHistory, SignalHistory
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response


log = get_logger(__name__)


class PlaybackController:
    """回放已記錄的模擬數據。"""

    @staticmethod
    @actor
    def list(request):  # noqa: A002
        """列出所有模擬 session。

        Returns:
            {
                sessions: [
                    {session_uuid, scene_id, status, created_at, ended_at, duration_ms}
                ]
            }
        """
        log.info("PlaybackController.list")

        try:
            sessions = SimulationSession.objects.all().order_by("-created_at")
            result = []

            for session in sessions:
                duration_ms = None
                if session.ended_at:
                    delta = session.ended_at - session.created_at
                    duration_ms = int(delta.total_seconds() * 1000)

                result.append(
                    {
                        "session_uuid": session.session_uuid,
                        "scene_id": session.scene_id,
                        "status": session.status,
                        "created_at": session.created_at.isoformat(),
                        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                        "duration_ms": duration_ms,
                    }
                )

            return success_response({"sessions": result})
        except Exception as e:
            log.exception("Failed to list sessions")
            return error_response(f"Failed to list sessions: {e}", {}, 500)

    @staticmethod
    @actor
    def read(request):
        """讀取特定 session 的完整數據。

        Body:
            {
                "session_uuid": str
            }

        Returns:
            {
                session_uuid, scene_id, status, created_at, ended_at,
                frames: [
                    {
                        ts: int (ms),
                        ues: [{name, x, y, z, rsrp_dbm, sinr_db}]
                    }
                ]
            }
        """
        data, error = parse_body(request)
        if error:
            return error

        session_uuid = data.get("session_uuid")
        if not session_uuid:
            return error_response("Missing session_uuid", {}, 400)

        log.info("PlaybackController.read session_uuid=%s", session_uuid)

        try:
            session = SimulationSession.objects.get(session_uuid=session_uuid)
        except SimulationSession.DoesNotExist:
            return error_response(f"Session {session_uuid} not found", {}, 404)

        try:
            # 讀取該 session 的所有信號記錄，按時間戳排序
            signals = SignalHistory.objects.filter(session_uuid=session_uuid).order_by("signal_ts")

            # 根據信號的時間戳分組，每個時間戳對應一個 frame
            frames_dict = {}
            for signal in signals:
                ts_ms = int(signal.signal_ts.timestamp() * 1000)
                if ts_ms not in frames_dict:
                    frames_dict[ts_ms] = {}

                frames_dict[ts_ms][signal.ue_name] = {
                    "name": signal.ue_name,
                    "serving_cell": signal.serving_cell,
                    "rsrp_dbm": signal.rsrp_dbm,
                    "sinr_db": signal.sinr_db,
                }

            # 同時讀取位置數據，補充 UE 的 x, y, z
            positions = PositionHistory.objects.filter(
                session_uuid=session_uuid,
                entity_type="ue",
            ).order_by("position_ts")

            # 建立位置時間戳的映射（使用最近的位置）
            latest_pos = {}
            for pos in positions:
                latest_pos[pos.entity_name] = {"x": pos.x, "y": pos.y, "z": pos.z}

            # 補充位置信息到每個 frame
            frames = []
            for ts_ms in sorted(frames_dict.keys()):
                frame_ues = []
                for ue_name, signal_data in frames_dict[ts_ms].items():
                    ue_data = signal_data.copy()
                    if ue_name in latest_pos:
                        ue_data.update(latest_pos[ue_name])
                    frame_ues.append(ue_data)

                frames.append({"ts": ts_ms, "ues": frame_ues})

            return success_response(
                {
                    "session_uuid": session.session_uuid,
                    "scene_id": session.scene_id,
                    "status": session.status,
                    "created_at": session.created_at.isoformat(),
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "frames": frames,
                }
            )
        except Exception as e:
            log.exception("Failed to read session data")
            return error_response(f"Failed to read session data: {e}", {}, 500)
