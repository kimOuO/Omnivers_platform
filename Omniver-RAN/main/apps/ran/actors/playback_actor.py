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
                    {session_uuid, scene_id, status, timestamp, ended_at, duration_ms, frame_count}
                ]
            }
        """
        log.info("PlaybackController.list")

        try:
            from django.db.models import Count, Q

            sessions = SimulationSession.objects.all().order_by("-created_at")
            result = []

            for session in sessions:
                duration_ms = None
                if session.ended_at:
                    delta = session.ended_at - session.created_at
                    duration_ms = int(delta.total_seconds() * 1000)

                # 計算 frame_count (distinct signal_ts)
                frame_count = SignalHistory.objects.filter(
                    session_uuid=session.session_uuid
                ).values("signal_ts").distinct().count()

                result.append(
                    {
                        "session_uuid": session.session_uuid,
                        "scene_id": session.scene_id,
                        "status": session.status,
                        "timestamp": session.created_at.isoformat(),  # 前端期望 timestamp 欄位
                        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                        "duration_ms": duration_ms,
                        "frame_count": frame_count,
                        "scene_snapshot": session.metadata_json.get("scene_snapshot", {}),
                    }
                )

            return success_response({"sessions": result})
        except Exception as e:
            log.exception("Failed to list sessions")
            return error_response(f"Failed to list sessions: {e}", {}, 500)

    @staticmethod
    @actor
    def read(request):
        """讀取特定 session 的單一 frame 或全部 frames。

        Body:
            {
                "session_uuid": str,
                "frame_index": int (optional, 0-based)
            }

        Returns (frame_index specified):
            {
                tick: int,
                ues: [{name, x, y, z, rsrp_dbm, sinr_db, serving_cell}],
                scene_snapshot: {...}
            }

        Returns (frame_index not specified):
            {
                session_uuid, scene_id, status, timestamp, ended_at,
                frames: [{tick, ues: [...]}],
                scene_snapshot: {...}
            }
        """
        data, error = parse_body(request)
        if error:
            return error

        session_uuid = data.get("session_uuid")
        frame_index = data.get("frame_index")
        if not session_uuid:
            return error_response("Missing session_uuid", {}, 400)

        log.info("PlaybackController.read session_uuid=%s frame_index=%s", session_uuid, frame_index)

        try:
            session = SimulationSession.objects.get(session_uuid=session_uuid)
        except SimulationSession.DoesNotExist:
            return error_response(f"Session {session_uuid} not found", {}, 404)

        try:
            # 取得 scene_snapshot（從 metadata_json）
            scene_snapshot = session.metadata_json.get("scene_snapshot", {})

            # 讀取該 session 的所有信號記錄，按時間戳排序
            signals = SignalHistory.objects.filter(session_uuid=session_uuid).order_by("signal_ts")

            # 根據信號的時間戳分組，每個時間戳對應一個 frame
            frames_dict = {}
            for signal in signals:
                ts = signal.signal_ts
                if ts not in frames_dict:
                    frames_dict[ts] = {}

                frames_dict[ts][signal.ue_name] = {
                    "name": signal.ue_name,
                    "serving_cell": signal.serving_cell,
                    "serving_gnb": signal.serving_gnb,
                    "serving_pci": signal.serving_pci,
                    "serving_cell_id": signal.serving_cell_id,
                    "rsrp_dbm": signal.rsrp_dbm,
                    "sinr_db": signal.sinr_db,
                }

            # 讀取位置數據
            all_positions = PositionHistory.objects.filter(
                session_uuid=session_uuid,
                entity_type="ue",
            ).order_by("position_ts")

            # 對每個 frame，補充最相近的位置數據
            sorted_timestamps = sorted(frames_dict.keys())

            def get_position_for_timestamp(ue_name: str, target_ts):
                """取得 target_ts 時或之前最近的 UE 位置。"""
                pos_record = all_positions.filter(
                    entity_name=ue_name,
                    position_ts__lte=target_ts,
                ).order_by("-position_ts").first()
                if pos_record:
                    return {"x": pos_record.x, "y": pos_record.y, "z": pos_record.z}
                return {}

            # 若指定 frame_index，僅返回該幀
            if frame_index is not None:
                if not isinstance(frame_index, int) or frame_index < 0 or frame_index >= len(sorted_timestamps):
                    return error_response(f"frame_index {frame_index} out of range [0, {len(sorted_timestamps) - 1}]", {}, 400)

                target_ts = sorted_timestamps[frame_index]
                frame_ues = []
                for ue_name, signal_data in frames_dict[target_ts].items():
                    ue_data = signal_data.copy()
                    pos = get_position_for_timestamp(ue_name, target_ts)
                    ue_data.update(pos)
                    frame_ues.append(ue_data)

                return success_response(
                    {
                        "tick": frame_index,
                        "ues": frame_ues,
                        "scene_snapshot": scene_snapshot,
                    }
                )

            # 若未指定 frame_index，返回所有 frames
            frames = []
            for i, ts in enumerate(sorted_timestamps):
                frame_ues = []
                for ue_name, signal_data in frames_dict[ts].items():
                    ue_data = signal_data.copy()
                    pos = get_position_for_timestamp(ue_name, ts)
                    ue_data.update(pos)
                    frame_ues.append(ue_data)

                frames.append({"tick": i, "ues": frame_ues})

            return success_response(
                {
                    "session_uuid": session.session_uuid,
                    "scene_id": session.scene_id,
                    "status": session.status,
                    "timestamp": session.created_at.isoformat(),
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "frames": frames,
                    "scene_snapshot": scene_snapshot,
                }
            )
        except Exception as e:
            log.exception("Failed to read session data")
            return error_response(f"Failed to read session data: {e}", {}, 500)
