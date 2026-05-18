"""PlaybackController — 回放功能（list / read）。"""
from __future__ import annotations

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import (
    ControlAction,
    HandoverHistory,
    PositionHistory,
    SignalHistory,
    SimulationSession,
)
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
                    "rsrp_map": signal.rsrp_map_json or {},
                    "throughput_dl_mbps": signal.throughput_dl_mbps,
                    "throughput_ul_mbps": signal.throughput_ul_mbps,
                    "mcs_dl": signal.mcs_dl,
                    "prb_used_dl": signal.prb_used_dl,
                    "mimo_rank": signal.mimo_rank,
                }

            # 讀取位置數據
            all_positions = PositionHistory.objects.filter(
                session_uuid=session_uuid,
                entity_type="ue",
            ).order_by("position_ts")

            # 讀取本 session 的 handover 事件,稍後依 event_ts 切到對應 frame
            all_handovers = list(
                HandoverHistory.objects.filter(session_uuid=session_uuid).order_by("event_ts")
            )
            # 讀取本 session 的 RIC control actions
            all_actions = list(
                ControlAction.objects.filter(session_uuid=session_uuid).order_by("action_ts")
            )

            # 對每個 frame，補充最相近的位置數據
            sorted_timestamps = sorted(frames_dict.keys())

            def _ho_to_dict(h):
                return {
                    "ho_uuid": h.ho_uuid,
                    "ue_name": h.ue_name,
                    "source_cell": h.source_cell,
                    "target_cell": h.target_cell,
                    "trigger": h.trigger,
                    "status": h.status,
                    "event_ts": h.event_ts.isoformat() if h.event_ts else None,
                }

            def handovers_in_window(start_ts, end_ts):
                """落在 (start_ts, end_ts] 區間內的 HO,代表 'frame 進入此 ts 之間發生'。"""
                out = []
                for h in all_handovers:
                    if h.event_ts is None:
                        continue
                    if start_ts is None:
                        if h.event_ts <= end_ts:
                            out.append(_ho_to_dict(h))
                    else:
                        if start_ts < h.event_ts <= end_ts:
                            out.append(_ho_to_dict(h))
                return out

            def _action_to_dict(a):
                return {
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

            def actions_in_window(start_ts, end_ts):
                out = []
                for a in all_actions:
                    if a.action_ts is None:
                        continue
                    if start_ts is None:
                        if a.action_ts <= end_ts:
                            out.append(_action_to_dict(a))
                    else:
                        if start_ts < a.action_ts <= end_ts:
                            out.append(_action_to_dict(a))
                return out

            # #5: 從 scene_snapshot 列出本 session 所有 cell,作為 cell_state 推算基底。
            known_cells: dict[str, dict] = {}
            for gnb in (scene_snapshot.get("gnbs") or []):
                for c in (gnb.get("cells") or []):
                    cid = c.get("cell_id") or c.get("name")
                    if cid:
                        known_cells[cid] = {
                            "cell_id": cid,
                            "gnb_id": gnb.get("name") or gnb.get("gnb_id"),
                            "pci": c.get("pci"),
                            "is_active": True,
                            "prb_quota": None,  # {min_prb, max_prb, dedicated_prb} 或 None
                        }
            # 補上 signal_history 出現過、但 scene_snapshot 漏記的 cell
            for ts in sorted_timestamps:
                for ue_data in frames_dict[ts].values():
                    cid = ue_data.get("serving_cell")
                    if cid and cid not in known_cells:
                        known_cells[cid] = {
                            "cell_id": cid,
                            "gnb_id": ue_data.get("serving_gnb"),
                            "pci": ue_data.get("serving_pci"),
                            "is_active": True,
                            "prb_quota": None,
                        }

            def compute_cell_states_at(target_ts):
                """Replay control_actions <= target_ts 來推算 frame_ts 當下每個 cell 的狀態。"""
                # deep copy
                state = {cid: dict(v) for cid, v in known_cells.items()}
                for a in all_actions:
                    if a.action_ts is None or a.action_ts > target_ts:
                        continue
                    payload = a.payload_json or {}
                    label = a.action_label or ""
                    if label == "CELL_DISABLE" and a.cell_id in state:
                        state[a.cell_id]["is_active"] = False
                    elif label == "CELL_ENABLE" and a.cell_id in state:
                        state[a.cell_id]["is_active"] = True
                    elif label == "PRB_QUOTA":
                        quota = {
                            "min_prb": payload.get("min_prb"),
                            "max_prb": payload.get("max_prb"),
                            "dedicated_prb": payload.get("dedicated_prb"),
                        }
                        targets = payload.get("cells") or ([a.cell_id] if a.cell_id else [])
                        for tc in targets:
                            if tc in state:
                                state[tc]["prb_quota"] = quota
                return state

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
                prev_ts = sorted_timestamps[frame_index - 1] if frame_index > 0 else None
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
                        "handovers": handovers_in_window(prev_ts, target_ts),
                        "control_actions": actions_in_window(prev_ts, target_ts),
                        "cell_states": list(compute_cell_states_at(target_ts).values()),
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

                prev_ts = sorted_timestamps[i - 1] if i > 0 else None
                frames.append({
                    "tick": i,
                    "ues": frame_ues,
                    "handovers": handovers_in_window(prev_ts, ts),
                    "control_actions": actions_in_window(prev_ts, ts),
                    "cell_states": list(compute_cell_states_at(ts).values()),
                })

            return success_response(
                {
                    "session_uuid": session.session_uuid,
                    "scene_id": session.scene_id,
                    "status": session.status,
                    "timestamp": session.created_at.isoformat(),
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "frames": frames,
                    "scene_snapshot": scene_snapshot,
                    "handovers": [_ho_to_dict(h) for h in all_handovers],
                    "control_actions": [_action_to_dict(a) for a in all_actions],
                }
            )
        except Exception as e:
            log.exception("Failed to read session data")
            return error_response(f"Failed to read session data: {e}", {}, 500)
