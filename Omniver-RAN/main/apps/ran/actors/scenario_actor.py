"""ScenarioController — Phase B fast-replay scenario CRUD + precompute trigger.

Endpoints:
  upload      POST body = scenario JSON,落地存 Scenario.raw_json
  list        POST → 列出所有 scenarios + 狀態
  read        POST {scenario_id} → 完整 raw_json + 狀態
  precompute  POST {scenario_id} → 標 status=pending 給 worker pickup(實際 Sionna 跑在 B.2)
  delete      POST {scenario_id} → 刪除(若 cache 已落地,連 parquet 一起刪)
"""
from __future__ import annotations

import os

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import BuildingObject, GnbConfig, Scenario, UeConfig
from main.apps.ran.services.business.kit_operations import KitBusinessService
from main.apps.ran.services.common.timestamp_service import TimestampService
from main.apps.ran.services.common.uuid_service import UUIDService
from main.apps.ran.services.optional.scene_config_generator import (
    SceneConfigGeneratorService,
)
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response


log = get_logger(__name__)

# 保留最多筆 scenario,超出後 LRU 刪最舊(連 cache 檔一起)
MAX_SCENARIOS = 20


def _delete_cache_file(scenario: "Scenario") -> bool:
    """刪 scenario 對應的 npz cache。回傳是否真的有檔被刪。"""
    if scenario.cache_path and os.path.exists(scenario.cache_path):
        try:
            os.remove(scenario.cache_path)
            return True
        except OSError as e:
            log.warning("Failed to delete cache %s: %s", scenario.cache_path, e)
    return False


def _prune_old_scenarios() -> int:
    """若超過 MAX_SCENARIOS,刪最舊的(LRU by created_at)直到 ≤ MAX_SCENARIOS。
    回傳刪掉的筆數。"""
    qs = Scenario.objects.order_by("created_at")
    count = qs.count()
    if count <= MAX_SCENARIOS:
        return 0
    n_to_delete = count - MAX_SCENARIOS
    deleted = 0
    for s in qs[:n_to_delete]:
        sid = s.scenario_id
        cache_was = s.cache_path
        _delete_cache_file(s)
        s.delete()
        log.info("LRU prune scenario %s (cache=%s)", sid, cache_was or "—")
        deleted += 1
    return deleted


def _validate_scenario_json(raw: dict) -> tuple[bool, str]:
    """最小欄位驗證 — schema 完整版見 docs/plan/fast-replay-mode.md B.1"""
    required = ["scenario_id", "scene_id", "duration_sec", "tick_ms", "ues"]
    for k in required:
        if k not in raw:
            return False, f"missing field: {k}"
    if not isinstance(raw["ues"], list) or len(raw["ues"]) == 0:
        return False, "ues must be non-empty list"
    for ue in raw["ues"]:
        if "name" not in ue or "positions" not in ue:
            return False, "each ue requires name and positions"
        if not isinstance(ue["positions"], list) or len(ue["positions"]) == 0:
            return False, f"ue {ue.get('name')} positions empty"
    # traffic 可選
    return True, ""


class ScenarioController:
    @staticmethod
    @actor
    def upload(request):
        """Body 直接是 scenario JSON。會覆寫同 scenario_id 的舊紀錄。"""
        data, error = parse_body(request)
        if error:
            return error

        ok, msg = _validate_scenario_json(data)
        if not ok:
            return error_response(f"Invalid scenario JSON: {msg}", {}, 400)

        scenario_id = str(data["scenario_id"])
        try:
            obj, created = Scenario.objects.update_or_create(
                scenario_id=scenario_id,
                defaults={
                    "scene_id": str(data["scene_id"]),
                    "raw_json": data,
                    "duration_sec": float(data["duration_sec"]),
                    "tick_ms": int(data["tick_ms"]),
                    "ue_count": len(data["ues"]),
                    # 上傳會 reset precompute state(舊 cache 失效)
                    "precompute_status": "pending",
                    "precompute_progress": 0.0,
                    "precompute_error": "",
                    "cache_path": "",
                    "cache_size_bytes": 0,
                },
            )
            log.info(
                "Scenario %s: scenario_id=%s scene_id=%s duration=%.1fs ues=%d tick=%dms",
                "created" if created else "updated", scenario_id, data["scene_id"],
                data["duration_sec"], len(data["ues"]), data["tick_ms"],
            )
            # 新建的話檢查是否超過上限,有就 LRU 刪舊
            pruned = 0
            if created:
                pruned = _prune_old_scenarios()
            return success_response(
                {
                    "scenario_id": obj.scenario_id,
                    "scene_id": obj.scene_id,
                    "duration_sec": obj.duration_sec,
                    "tick_ms": obj.tick_ms,
                    "ue_count": obj.ue_count,
                    "precompute_status": obj.precompute_status,
                    "created": created,
                    "pruned_old": pruned,
                    "max_scenarios": MAX_SCENARIOS,
                },
                message=(
                    f"Scenario {'created' if created else 'updated'}"
                    + (f" — LRU pruned {pruned} old" if pruned > 0 else "")
                ),
                status=201 if created else 200,
            )
        except Exception as e:
            log.exception("Failed to upload scenario")
            return error_response(f"Failed to upload scenario: {e}", {}, 500)

    @staticmethod
    @actor
    def list(request):
        """列出所有 scenarios 摘要(不含 raw_json,避免 payload 太大)。"""
        _data, error = parse_body(request)
        if error:
            return error
        rows = [
            {
                "scenario_id": s.scenario_id,
                "scene_id": s.scene_id,
                "duration_sec": s.duration_sec,
                "tick_ms": s.tick_ms,
                "ue_count": s.ue_count,
                "precompute_status": s.precompute_status,
                "precompute_progress": s.precompute_progress,
                "precompute_error": s.precompute_error,
                "cache_path": s.cache_path,
                "cache_size_bytes": s.cache_size_bytes,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in Scenario.objects.all()
        ]
        return success_response({"scenarios": rows, "count": len(rows)})

    @staticmethod
    @actor
    def read(request):
        """讀單一 scenario 含完整 raw_json。"""
        data, error = parse_body(request)
        if error:
            return error
        scenario_id = data.get("scenario_id")
        if not scenario_id:
            return error_response("Missing scenario_id", {}, 400)
        try:
            s = Scenario.objects.get(scenario_id=scenario_id)
        except Scenario.DoesNotExist:
            return error_response(f"Scenario {scenario_id} not found", {}, 404)
        return success_response({
            "scenario_id": s.scenario_id,
            "scene_id": s.scene_id,
            "duration_sec": s.duration_sec,
            "tick_ms": s.tick_ms,
            "ue_count": s.ue_count,
            "precompute_status": s.precompute_status,
            "precompute_progress": s.precompute_progress,
            "precompute_error": s.precompute_error,
            "cache_path": s.cache_path,
            "cache_size_bytes": s.cache_size_bytes,
            "raw_json": s.raw_json,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        })

    @staticmethod
    @actor
    def apply_to_scene(request):
        """把劇本拓樸寫進 Omniverse 場景表(GnbConfig/UeConfig/BuildingObject),
        讓 Scene Editor 的 Scene Layout 與 3D(scene_config→Kit)反映該劇本場景。

        ★ 會「覆蓋」目前場景表(整批清掉再依劇本重建)—— 這是「選劇本即套用」
          的語意:場景=劇本拓樸,不保留手動編輯。

        Body: {scenario_id}
        座標慣例:劇本 position=[x, y(height), z];UE positions=[t, x, y, z]
        (套用時丟掉時間軸 t,waypoints 存 [x,y,z])。
        """
        data, error = parse_body(request)
        if error:
            return error
        scenario_id = data.get("scenario_id")
        if not scenario_id:
            return error_response("Missing scenario_id", {}, 400)
        try:
            s = Scenario.objects.get(scenario_id=scenario_id)
        except Scenario.DoesNotExist:
            return error_response(f"Scenario {scenario_id} not found", {}, 404)

        raw = s.raw_json or {}
        ts = TimestampService.get_current_timestamp()
        try:
            # 1) 整批清掉舊場景表(覆蓋語意)
            GnbConfig.objects.all().delete()
            UeConfig.objects.all().delete()
            BuildingObject.objects.all().delete()

            # 2) gNBs(含 cells[] per-sector)
            n_gnb = 0
            for g in raw.get("gnbs", []) or []:
                name = g.get("name")
                if not name:
                    continue
                pos = g.get("position", [0, 0, 0]) or [0, 0, 0]
                GnbConfig.objects.create(
                    gnb_uuid=UUIDService.generate_uuid("gnb", name),
                    name=name,
                    freq_mhz=float(g.get("frequency_ghz", 3.5)) * 1000.0,
                    power_dbm=float(g.get("power_dbm", 10.0)),
                    bw_hz=float(g.get("bandwidth_mhz", 40.0)) * 1_000_000.0,
                    active=bool(g.get("active", True)),
                    pos_x=float(pos[0]), pos_y=float(pos[1]), pos_z=float(pos[2]),
                    cells=g.get("cells") or [],
                    gnb_created_at=ts, gnb_updated_at=ts,
                )
                n_gnb += 1

            # 3) UEs(positions=[t,x,y,z] → 首點為 pos,全部去 t 存 waypoints)
            n_ue = 0
            for u in raw.get("ues", []) or []:
                name = u.get("name")
                positions = u.get("positions") or []
                if not name or not positions:
                    continue
                # 劇本 positions 有兩種格式:[t,x,y,z](自帶時戳)與 [x,y,z](沒時戳)。
                # 原本寫死讀 p[1..3],遇到 3 元素會 IndexError → 整批 UE 的航點掉光,
                # 套用後從 /editor 跑就全是靜止單點(2026-08-24 anr_missing_meas 踩到:
                # 五個 UE 只有手繪的那個會動,其餘四個 waypoints=0)。
                wps = [
                    [float(q[1]), float(q[2]), float(q[3])] if len(q) >= 4
                    else [float(q[0]), float(q[1]), float(q[2])]
                    for q in positions if len(q) >= 3
                ]
                if not wps:
                    continue
                first = wps[0]
                # 帶上劇本自己指定的身高與速度。少了這兩個欄位，Kit 會走
                # _build_ue 的 fallback 把人放大到 34 m（那是城市尺度的預設值），
                # 室內劇本套用後人就會比走廊還高。
                UeConfig.objects.create(
                    ue_uuid=UUIDService.generate_uuid("ue", name),
                    name=name,
                    waypoints_json=wps,
                    pos_x=first[0], pos_y=first[1], pos_z=first[2],
                    speed_mps=float(u.get("speed_mps") or 1.0),
                    target_height_m=(float(u["target_height_m"])
                                     if u.get("target_height_m") is not None else None),
                    loop=bool(u.get("loop", False)),
                    ue_created_at=ts, ue_updated_at=ts,
                )
                n_ue += 1

            # 4) Buildings(劇本若無 buildings 則場景無建築 = open field)
            n_bld = 0
            for b in raw.get("buildings", []) or []:
                name = b.get("name")
                if not name:
                    continue
                pos = b.get("position", [0, 0, 0]) or [0, 0, 0]
                size = b.get("size", [10, 10, 10]) or [10, 10, 10]
                BuildingObject.objects.create(
                    building_uuid=UUIDService.generate_uuid("building", name),
                    name=name,
                    scene_id=str(raw.get("scene_id", "")),
                    pos_x=float(pos[0]), pos_y=float(pos[1]), pos_z=float(pos[2]),
                    size_x=float(size[0]), size_y=float(size[1]), size_z=float(size[2]),
                    building_created_at=ts, building_updated_at=ts,
                )
                n_bld += 1

            # 5) 重新產生 scene_config 並推給 Kit / Omniverse(3D 同步)
            kit_ok = True
            kit_err = ""
            try:
                config = SceneConfigGeneratorService.generate()
                KitBusinessService.push_scene_config(config)
            except Exception as e:  # noqa: BLE001
                kit_ok = False
                kit_err = str(e)
                log.warning("apply_to_scene: Kit push failed (場景表已更新): %s", e)

            log.info(
                "Scenario %s applied to scene: gnbs=%d ues=%d buildings=%d kit=%s",
                scenario_id, n_gnb, n_ue, n_bld, "ok" if kit_ok else "fail",
            )
            return success_response(
                {
                    "scenario_id": scenario_id,
                    "gnbs": n_gnb, "ues": n_ue, "buildings": n_bld,
                    "kit_pushed": kit_ok, "kit_error": kit_err,
                },
                message=f"Scene populated from scenario {scenario_id}",
            )
        except Exception as e:
            log.exception("apply_to_scene failed")
            return error_response(f"apply_to_scene failed: {e}", {}, 500)

    @staticmethod
    @actor
    def apply_time(request):
        """把劇本在某個時刻的「在場名單」套到 Kit —— 不在場的 UE 設為隱形。

        為什麼需要這支：劇本的 UE 清單是固定的，離場只能靠「停到走廊外」表達，
        prim 一直存在。Kit 自己的動畫是累積位移、沒有絕對時鐘，算不出
        「幾點該有幾個人」，所以由後端讀劇本的 active 時間軸再推給 Kit。

        Body: {scenario_id, t_sec}
        t_sec 可以超過 duration_sec，會自動取模（方便循環播放）。
        """
        data, error = parse_body(request)
        if error:
            return error
        scenario_id = data.get("scenario_id")
        if not scenario_id:
            return error_response("Missing scenario_id", {}, 400)
        try:
            t = float(data.get("t_sec", 0))
        except (TypeError, ValueError):
            return error_response("t_sec 需為數字", {}, 400)
        try:
            sc = Scenario.objects.get(scenario_id=scenario_id)
        except Scenario.DoesNotExist:
            return error_response(f"Scenario {scenario_id} not found", {}, 404)

        raw = sc.raw_json or {}
        dur = float(raw.get("duration_sec") or 0) or 86400.0
        t = t % dur

        present, absent, no_window = [], [], []
        for u in raw.get("ues", []) or []:
            name = u.get("name")
            if not name:
                continue
            windows = u.get("active")
            if not windows:
                # 沒有 active 時間軸的劇本一律當成全程在場，維持舊行為
                no_window.append(name)
                present.append(name)
                continue
            if any(float(a) <= t < float(b) for a, b in windows):
                present.append(name)
            else:
                absent.append(name)

        ok, failed = 0, []
        for name in present:
            if KitBusinessService.set_ue_visible(name, True):
                ok += 1
            else:
                failed.append(name)
        for name in absent:
            if KitBusinessService.set_ue_visible(name, False):
                ok += 1
            else:
                failed.append(name)

        hh, mm = int(t // 3600), int((t % 3600) // 60)
        log.info("apply_time %s @ %02d:%02d — 在場 %d / 離場 %d",
                 scenario_id, hh, mm, len(present), len(absent))
        return success_response(
            {"scenario_id": scenario_id, "t_sec": round(t, 1),
             "clock": f"{hh:02d}:{mm:02d}",
             "present": present, "absent": absent,
             "present_count": len(present), "absent_count": len(absent),
             "ues_without_active_window": no_window,
             "kit_calls_ok": ok, "kit_calls_failed": failed},
            message=f"{hh:02d}:{mm:02d} — 在場 {len(present)} 人、離場 {len(absent)} 人已隱藏",
        )

    @staticmethod
    @actor
    def precompute(request):
        """觸發 Sionna 離線計算。Phase B MVP 只把 status 標成 pending,
        實際 worker(physics container 內 run_precompute.py)會自動 pickup。

        Body: {scenario_id}
        """
        data, error = parse_body(request)
        if error:
            return error
        scenario_id = data.get("scenario_id")
        if not scenario_id:
            return error_response("Missing scenario_id", {}, 400)
        try:
            s = Scenario.objects.get(scenario_id=scenario_id)
        except Scenario.DoesNotExist:
            return error_response(f"Scenario {scenario_id} not found", {}, 404)

        if s.precompute_status == "running":
            return error_response(
                f"Scenario {scenario_id} already running precompute", {}, 409
            )

        s.precompute_status = "pending"
        s.precompute_progress = 0.0
        s.precompute_error = ""
        s.cache_path = ""
        s.cache_size_bytes = 0
        s.save(update_fields=[
            "precompute_status", "precompute_progress",
            "precompute_error", "cache_path", "cache_size_bytes",
        ])
        log.info("Scenario %s: precompute requested (status=pending)", scenario_id)
        return success_response(
            {"scenario_id": scenario_id, "precompute_status": "pending"},
            message="Precompute job queued",
        )

    @staticmethod
    @actor
    def update_status(request):
        """Precompute worker callback — 更新單個 scenario 的 status / progress / cache。

        Body: {
            scenario_id,
            precompute_status?: pending|running|ready|failed,
            precompute_progress?: float (0~100),
            precompute_error?: str,
            cache_path?: str,
            cache_size_bytes?: int,
        }
        """
        data, error = parse_body(request)
        if error:
            return error
        scenario_id = data.get("scenario_id")
        if not scenario_id:
            return error_response("Missing scenario_id", {}, 400)
        try:
            s = Scenario.objects.get(scenario_id=scenario_id)
        except Scenario.DoesNotExist:
            return error_response(f"Scenario {scenario_id} not found", {}, 404)
        updates = []
        for field in (
            "precompute_status", "precompute_progress",
            "precompute_error", "cache_path", "cache_size_bytes",
        ):
            if field in data:
                setattr(s, field, data[field])
                updates.append(field)
        if updates:
            s.save(update_fields=updates)
            log.info("Scenario %s status update: %s", scenario_id, updates)
        return success_response({
            "scenario_id": s.scenario_id,
            "precompute_status": s.precompute_status,
            "precompute_progress": s.precompute_progress,
            "cache_path": s.cache_path,
        })

    @staticmethod
    @actor
    def delete(request):
        """刪除 scenario,順手刪 parquet。Body: {scenario_id}"""
        data, error = parse_body(request)
        if error:
            return error
        scenario_id = data.get("scenario_id")
        if not scenario_id:
            return error_response("Missing scenario_id", {}, 400)
        try:
            s = Scenario.objects.get(scenario_id=scenario_id)
        except Scenario.DoesNotExist:
            return error_response(f"Scenario {scenario_id} not found", {}, 404)
        _delete_cache_file(s)
        s.delete()
        log.info("Scenario %s deleted", scenario_id)
        return success_response(
            {"scenario_id": scenario_id}, message="Scenario deleted",
        )
