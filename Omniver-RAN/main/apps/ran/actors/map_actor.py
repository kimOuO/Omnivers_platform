"""MapController — 由 OpenStreetMap bbox 產生地圖 USD 場景並套用到 Kit。

Endpoints:
  generate       POST {name, min_lon, min_lat, max_lon, max_lat, label?}
                 → Overpass 抓 OSM → 轉 USD → 存 assets/maps/{name}.usd + DB(同步)
  list           POST → 列出所有地圖 + 狀態
  read           POST {name} → 單一地圖詳情
  apply_to_scene POST {name} → 注入 environment.template_usd + skip_buildings 推給 Kit
  import_glb     POST multipart{file, name, label?, scale?} → 上傳 .glb 轉 USD 註冊成地圖
  delete         POST {name} → 刪 DB row + USD 檔（含貼圖資料夾）
"""
from __future__ import annotations

import hashlib
import os
import re

from django.http import FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

import numpy as np

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import BuildingObject, GnbConfig, MapScene, UeConfig
from main.apps.ran.services.business.kit_operations import KitBusinessService
from main.apps.ran.services.optional.glb_to_mitsuba import build_mitsuba_from_labels
from main.apps.ran.services.optional.glb_to_usd import GlbError, convert_glb_to_usd
from main.apps.ran.services.optional.scan_material_classifier import classify_and_record
from main.apps.ran.services.optional.scan_walkable import (
    ScanGrid,
    WalkableError,
    plan_scan_path,
)
from main.apps.ran.services.optional.osm_to_usd import convert_osm_to_usd
from main.apps.ran.services.optional.nominatim_client import geocode as nominatim_geocode
from main.apps.ran.services.optional.overpass_client import fetch_osm
from main.apps.ran.services.optional.scene_config_generator import (
    SceneConfigGeneratorService,
)
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response

log = get_logger(__name__)

# USD 輸出目錄 — 需為 Kit 容器同路徑解析得到的絕對路徑(同路徑 bind mount)
MAPS_DIR = os.environ.get(
    "MAPS_DIR", "/home/mitlab/XAPP_DT/Omnivers_platform/assets/maps"
)
# Physics(Sionna)—— 套用地圖時同步把該地圖的 Mitsuba 場景推過去
PHYSICS_URL = os.environ.get("PHYSICS_URL", "http://host.docker.internal:8104")
# 匯入網格上限 —— 貼圖內嵌的掃描檔很容易破百 MB，擋在轉檔前比 OOM 好
MAX_GLB_BYTES = int(os.environ.get("MAX_GLB_BYTES", 300 * 1024 * 1024))


def _mitsuba_path_for(usd_path: str) -> str:
    """地圖 USD → 同名 Mitsuba XML(轉換器同時產出,同一份幾何/原點)。"""
    return os.path.splitext(usd_path)[0] + ".mitsuba.xml"


def _push_scene_to_physics(m: "MapScene", config: dict) -> tuple[bool, str]:
    """走 Physics 既有的 push_scene 管線,只是 geometry_source 用 mitsuba_xml_path,
    讓 Sionna 直接載入地圖的真實 mesh(而非 buildings_json 的方塊)。"""
    import requests

    mitsuba = _mitsuba_path_for(m.usd_path)
    if not os.path.exists(mitsuba):
        return False, f"Mitsuba 場景不存在(需重新產生地圖):{mitsuba}"

    gnbs = []
    for i, g in enumerate(config.get("gnbs", []) or []):
        pos = g.get("position", [0, 0, 0]) or [0, 0, 0]
        gnbs.append({
            "name": g.get("name", f"gnb{i}"),
            "pci": int(g.get("pci", i)),
            "cell_id": str(g.get("cell_id", g.get("name", f"cell{i}"))),
            "position": [float(pos[0]), float(pos[1]), float(pos[2])],
            "frequency_ghz": float(g.get("frequency_ghz", 3.5)),
            "power_dbm": float(g.get("power_dbm", 10.0)),
            "bandwidth_mhz": float(g.get("bandwidth_mhz", 40.0)),
        })
    payload = {
        "scene_id": m.name,
        "override_mode": "full" if gnbs else "geometry_only",
        "geometry_source": {"type": "mitsuba_xml_path", "path": mitsuba},
    }
    if gnbs:
        payload["gnbs"] = gnbs
    try:
        r = requests.post(
            f"{PHYSICS_URL}/api/v0.1/Physics/RanSignal/ConfigManager/push_scene",
            json=payload, timeout=120,
        )
        if r.status_code >= 400:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, str(e)

_NAME_RE = re.compile(r"[^A-Za-z0-9_\-]")


def _safe_name(name: str) -> str:
    """地圖名 → 安全檔名。

    中文地名的每個字都不在白名單裡,會被逐字換成 "_" —— 於是**同字數的中文名
    必然撞同一個檔名**:「國立臺灣大學」與「臺灣科技大學」都變 "______.usd",
    後產生的直接蓋掉前一個,套用時兩者指向同一份幾何(2026-08-20 實際踩到)。
    名稱一旦被改寫就補上原名的短雜湊,確保一名一檔。
    """
    raw = name.strip()
    safe = _NAME_RE.sub("_", raw)
    if safe != raw:
        safe = f"{safe}_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:6]}"
    return safe


def _glb_path_for(usd_path: str) -> str:
    """匯入地圖的原始 GLB 與 USD 同名同目錄。"""
    return os.path.splitext(usd_path)[0] + ".glb" if usd_path else ""


def _mesh_url_for(usd_path: str) -> str:
    """有留原始 GLB 才給下載 URL；OSM 產生的地圖沒有這個檔，回空字串。"""
    glb = _glb_path_for(usd_path)
    if not glb or not os.path.exists(glb):
        return ""
    return f"/api/v0.1/RAN/Map/MapController/mesh/{os.path.basename(glb)}"


def _row(m: "MapScene") -> dict:
    return {
        "name": m.name, "label": m.label,
        "min_lon": m.min_lon, "min_lat": m.min_lat,
        "max_lon": m.max_lon, "max_lat": m.max_lat,
        "usd_path": m.usd_path, "status": m.status, "error": m.error,
        "active": m.active,
        "building_count": m.building_count, "height_max_m": m.height_max_m,
        "extent_ew_m": m.extent_ew_m, "extent_ns_m": m.extent_ns_m,
        "created_at": m.created_at.isoformat(),
        "updated_at": m.updated_at.isoformat(),
        # 匯入的地圖會把原始 .glb 留在 USD 旁邊，前端 3D 視圖直接載這份
        # （瀏覽器沒有 USD 載入器，重新從 USD 轉回 glTF 不划算）
        "mesh_url": _mesh_url_for(m.usd_path),
        "indoor_mode": m.indoor_mode,
        "gnb_visual_scale": m.gnb_visual_scale,
    }


class MapController:
    @staticmethod
    @actor
    def geocode(request):
        """地標名稱 → 候選地點(座標 + 建議 bbox),給前端自動填 4 座標。
        Body: {query, limit?}
        走 Nominatim(openstreetmap.org 搜尋框同源服務),bbox 已正規化成
        適合做場景的大小(最小 ~500m、上限對齊 generate 的 3km 防呆)。
        """
        data, error = parse_body(request)
        if error:
            return error
        query = (data.get("query") or "").strip()
        if not query:
            return error_response("Missing query", {}, 400)
        try:
            results = nominatim_geocode(query, limit=int(data.get("limit") or 5))
            return success_response({"results": results, "count": len(results)})
        except Exception as e:  # noqa: BLE001
            log.warning("geocode '%s' failed: %s", query, e)
            return error_response(f"地標搜尋失敗:{e}", {}, 502)

    @staticmethod
    @actor
    def generate(request):
        """輸入 name + 4 座標 → 抓 OSM → 轉 USD → 存檔 + DB(同步,完成才回)。"""
        data, error = parse_body(request)
        if error:
            return error
        name = data.get("name")
        if not name or not str(name).strip():
            return error_response("Missing name", {}, 400)
        try:
            min_lon = float(data["min_lon"]); min_lat = float(data["min_lat"])
            max_lon = float(data["max_lon"]); max_lat = float(data["max_lat"])
        except (KeyError, TypeError, ValueError):
            return error_response(
                "需要 min_lon / min_lat / max_lon / max_lat(數字)", {}, 400
            )
        if min_lon >= max_lon or min_lat >= max_lat:
            return error_response("座標範圍無效(min 必須 < max)", {}, 400)
        # 防呆:範圍過大(> 約 3km)Overpass 會很慢/爆量
        if (max_lat - min_lat) > 0.03 or (max_lon - min_lon) > 0.03:
            return error_response(
                "範圍過大(建議 < 0.03 度 ≈ 3km),請縮小 bbox", {}, 400
            )

        safe = _safe_name(str(name))
        usd_path = os.path.join(MAPS_DIR, f"{safe}.usd")

        m, _ = MapScene.objects.update_or_create(
            name=str(name).strip(),
            defaults={
                "label": str(data.get("label") or name),
                "min_lon": min_lon, "min_lat": min_lat,
                "max_lon": max_lon, "max_lat": max_lat,
                "status": "pending", "error": "", "usd_path": usd_path,
            },
        )
        try:
            log.info("MapGen %s: Overpass 抓取 bbox=(%.5f,%.5f,%.5f,%.5f)",
                     name, min_lat, min_lon, max_lat, max_lon)
            osm_xml = fetch_osm(min_lat, min_lon, max_lat, max_lon)
            os.makedirs(MAPS_DIR, exist_ok=True)
            stats = convert_osm_to_usd(
                osm_xml, (min_lat, min_lon, max_lat, max_lon), usd_path
            )
            m.status = "ready"
            m.building_count = stats["building_count"]
            m.height_max_m = stats["height_max_m"]
            m.extent_ew_m = stats["extent_ew_m"]
            m.extent_ns_m = stats["extent_ns_m"]
            m.error = ""
            m.save()
            log.info("MapGen %s: ready — %d 棟, %.0fx%.0f m → %s",
                     name, stats["building_count"],
                     stats["extent_ew_m"], stats["extent_ns_m"], usd_path)
            return success_response(
                _row(m), message=f"地圖 {name} 產生完成({stats['building_count']} 棟)",
                status=201,
            )
        except Exception as e:  # noqa: BLE001
            log.exception("MapGen %s 失敗", name)
            m.status = "failed"
            m.error = str(e)
            m.save(update_fields=["status", "error", "updated_at"])
            return error_response(f"地圖產生失敗:{e}", {"name": name}, 500)

    @staticmethod
    @actor
    def import_glb(request):
        """上傳 .glb 掃描/建模檔 → 轉 USD → 註冊成一張地圖（可直接 apply_to_scene）。

        走 multipart/form-data 而非 JSON：GLB 動輒數十 MB，base64 進 JSON 會膨脹
        1/3 且整包吃進記憶體；multipart 讓 Django 自動落地成暫存檔。
        Fields: file=<glb>, name, label?, scale?, recenter?
        """
        upload = request.FILES.get("file")
        if upload is None:
            return error_response("需要上傳 file(.glb)", {}, 400)
        name = (request.POST.get("name") or "").strip()
        if not name:
            return error_response("Missing name", {}, 400)
        if upload.size > MAX_GLB_BYTES:
            return error_response(
                f"檔案過大({upload.size / 1e6:.0f} MB)，上限 {MAX_GLB_BYTES / 1e6:.0f} MB", {}, 413
            )
        try:
            scale = float(request.POST.get("scale") or 1.0)
        except ValueError:
            return error_response("scale 需為數字", {}, 400)
        if scale <= 0:
            return error_response("scale 需大於 0", {}, 400)
        recenter = str(request.POST.get("recenter", "true")).lower() not in ("false", "0", "")
        # 關掉可省約 4 秒（15 張 4K 貼圖要解碼），但這張地圖就無法推給 Sionna
        radio_materials = str(request.POST.get("radio_materials", "true")).lower() not in ("false", "0", "")
        # conservative（預設）只判 concrete + wood，其餘保守回退；
        # legacy_color 會額外用色彩判 glass/metal —— 實測全是誤判，只留作比對用
        material_mode = str(request.POST.get("material_mode", "conservative"))
        if material_mode not in ("conservative", "legacy_color"):
            return error_response("material_mode 需為 conservative 或 legacy_color", {}, 400)

        safe = _safe_name(name)
        usd_path = os.path.join(MAPS_DIR, f"{safe}.usd")

        # bbox 對匯入的網格沒有意義（沒有地理座標），但 MapScene 欄位不可為空 → 填 0
        m, _ = MapScene.objects.update_or_create(
            name=name,
            defaults={
                "label": str(request.POST.get("label") or name),
                "min_lon": 0.0, "min_lat": 0.0, "max_lon": 0.0, "max_lat": 0.0,
                "status": "pending", "error": "", "usd_path": usd_path,
            },
        )
        try:
            os.makedirs(MAPS_DIR, exist_ok=True)
            blob = upload.read()
            # 原始 GLB 一併留下：前端 3D 視圖要靠它顯示（瀏覽器讀不了 USD）
            with open(_glb_path_for(usd_path), "wb") as fh:
                fh.write(blob)
            stats = convert_glb_to_usd(
                blob, usd_path,
                prim_name=safe if safe[0].isalpha() or safe[0] == "_" else f"_{safe}",
                scale=scale, recenter=recenter, ground_align=recenter,
            )
            # 依貼圖色彩 + 幾何朝向分出 itu_* radio material，並產生 Mitsuba 場景。
            # 產在這裡的用意：檔名與 _mitsuba_path_for() 對得上，
            # apply_to_scene 既有的 _push_scene_to_physics() 就會自動推給 Sionna，
            # 不用為匯入網格另開一條推送路徑。
            radio = None
            if radio_materials:
                try:
                    radio = classify_and_record(
                        blob, os.path.splitext(usd_path)[0], mode=material_mode
                    )
                    radio["mitsuba"] = build_mitsuba_from_labels(
                        radio["npz_path"], _mitsuba_path_for(usd_path),
                        recenter=recenter, ground_align=recenter,
                    )
                except Exception as e:  # noqa: BLE001
                    # 分類失敗不該讓整個匯入失敗 —— USD 已經好了，Kit 顯示不受影響，
                    # 只是這張地圖不能推給 Sionna
                    log.warning("ImportGLB %s: 材質分類/Mitsuba 產生失敗（USD 仍可用）: %s", name, e)
                    radio = {"error": str(e)}

            m.status = "ready"
            m.building_count = stats["mesh_count"]
            m.height_max_m = stats["height_max_m"]
            m.extent_ew_m = stats["extent_ew_m"]
            m.extent_ns_m = stats["extent_ns_m"]
            m.error = ""
            m.save()
            log.info("ImportGLB %s: ready — %d mesh / %d tri, %.1fx%.1f m → %s",
                     name, stats["mesh_count"], stats["triangle_count"],
                     stats["extent_ew_m"], stats["extent_ns_m"], usd_path)
            row = _row(m)
            row["import_stats"] = stats
            row["radio_materials"] = radio
            return success_response(
                row,
                message=(
                    f"{name} 匯入完成（{stats['mesh_count']} mesh / "
                    f"{stats['triangle_count']} 三角形）。"
                    + (
                        f"材質已分類（{radio['mitsuba']['holes_capped']} 個破洞已封、"
                        f"{radio['evidence']['proven_area_pct']}% 面積有證據支持、"
                        f"{radio['evidence']['fallback_area_pct']}% 保守回退），"
                        "套用場景時會一併推給 Sionna。"
                        if radio and "mitsuba" in radio
                        else "材質分類未產生，這張地圖不會推給 Sionna（僅供 Kit 顯示）。"
                    )
                ),
                status=201,
            )
        except GlbError as e:
            m.status = "failed"; m.error = str(e)
            m.save(update_fields=["status", "error", "updated_at"])
            return error_response(f"GLB 解析失敗:{e}", {"name": name}, 400)
        except Exception as e:  # noqa: BLE001
            log.exception("ImportGLB %s 失敗", name)
            m.status = "failed"; m.error = str(e)
            m.save(update_fields=["status", "error", "updated_at"])
            return error_response(f"匯入失敗:{e}", {"name": name}, 500)

    @staticmethod
    @csrf_exempt
    @require_http_methods(["GET"])
    def mesh(request, filename: str):
        """提供匯入地圖的原始 .glb 給前端 3D 視圖載入（唯一的 GET 檔案端點）。

        走 FileResponse 串流而非讀進記憶體：掃描檔動輒數十 MB。
        """
        # 只認 basename 且限定副檔名 —— 這是唯一吃使用者字串去組路徑的地方，
        # 不擋就等於把 MAPS_DIR 以外的檔案也開放出去
        base = os.path.basename(filename)
        if base != filename or not base.endswith(".glb"):
            return error_response("Invalid filename", {}, 400)
        path = os.path.join(MAPS_DIR, base)
        if not os.path.exists(path):
            return error_response(f"Mesh {base} not found", {}, 404)
        resp = FileResponse(open(path, "rb"), content_type="model/gltf-binary")
        resp["Content-Length"] = os.path.getsize(path)
        resp["Cache-Control"] = "public, max-age=3600"
        return resp

    @staticmethod
    @actor
    def setup_indoor(request):
        """把場景切換成「室內尺度」，讓人與基站真的放得進走廊裡。

        平台原本的場景是城市尺度：gNB 掛在 30 m 高塔上、UE 在 Kit 裡被自動
        放大到 34 m 高（Kit `_build_ue` 的 fallback 常數）、位置散在 ±170 m。
        套用室內掃描後，這些物件全在 14 x 6 x 65 m 的走廊外面，畫面上根本
        找不到人在哪。

        這支端點做三件事：
          1) 從掃描 USD 算出可走區域（地板帶有面、身體帶無面、再留肩寬）
          2) UE 設 target_height_m=1.7（Kit 會據此自己算縮放倍率，不用手調 scale），
             位置放到可走格點上，軌跡改成沿走廊來回巡走 —— 路徑走 A*，不穿牆
          3) gNB 移進走廊、降到室內小基站高度與功率

        Body: {name, ue_height_m?, gnb_height_m?, gnb_power_dbm?, walk_speed_mps?,
               cell_m?, clearance_m?, dry_run?}
        dry_run=true 只回報會怎麼改，不寫入 DB。
        """
        data, error = parse_body(request)
        if error:
            return error
        name = data.get("name")
        if not name:
            return error_response("Missing name", {}, 400)
        try:
            m = MapScene.objects.get(name=name)
        except MapScene.DoesNotExist:
            return error_response(f"Map {name} not found", {}, 404)
        if m.status != "ready" or not m.usd_path or not os.path.exists(m.usd_path):
            return error_response(f"Map {name} 尚未 ready", {}, 409)

        ue_h = float(data.get("ue_height_m", 1.7))
        gnb_h = float(data.get("gnb_height_m", 2.5))
        gnb_power = float(data.get("gnb_power_dbm", 10.0))
        speed = float(data.get("walk_speed_mps", 1.2))
        # gNB 塔身半徑 3 m、輻射環半徑 14/22/30 m 都是這個值的倍數，
        # 城市尺度的 1.0 放進 6 m 高的走廊會整個塞爆 → 室內預設縮到 0.15
        gnb_visual_scale = float(data.get("gnb_visual_scale", 0.15))
        cell_m = float(data.get("cell_m", 0.25))
        clearance_m = float(data.get("clearance_m", 0.35))
        dry_run = bool(data.get("dry_run", False))

        try:
            grid = ScanGrid(m.usd_path, cell=cell_m, clearance=clearance_m)
            start, goal = grid.extremes_along_length()
            path = plan_scan_path(grid, start, goal)
        except WalkableError as e:
            return error_response(f"可走區域計算失敗:{e}", {"name": name}, 422)

        wp = path["waypoints"]
        if len(wp) < 2:
            return error_response("規劃出的路徑不足兩點", {"name": name}, 422)
        # 來回巡走：去程 + 回程，Kit 的動畫是 loop，這樣人會在走廊裡來回走
        round_trip = wp + list(reversed(wp))[1:]

        ues = list(UeConfig.objects.all().order_by("id"))
        gnbs = list(GnbConfig.objects.all().order_by("id"))
        changes = {"ues": [], "gnbs": []}

        for k, u in enumerate(ues):
            # 每個 UE 從路徑上不同位置出發，避免全部疊在同一點
            offset = (k * max(1, len(round_trip) // max(1, len(ues)))) % len(round_trip)
            rotated = round_trip[offset:] + round_trip[:offset]
            sx, _sy, sz = rotated[0]
            changes["ues"].append({
                "name": u.name,
                "from": [round(u.pos_x, 1), round(u.pos_y, 1), round(u.pos_z, 1)],
                "to": [round(sx, 2), 0.0, round(sz, 2)],
                "target_height_m": ue_h,
                "waypoints": len(rotated),
            })
            if not dry_run:
                u.pos_x, u.pos_y, u.pos_z = float(sx), 0.0, float(sz)
                u.target_height_m = ue_h
                u.waypoints_json = rotated
                u.speed_mps = speed
                u.loop = True
                u.save()

        # gNB 沿走廊長軸平均分布，掛在天花板下方
        pts = grid.walkable_points()
        axis = 0 if (pts[:, 0].max() - pts[:, 0].min()) >= (pts[:, 1].max() - pts[:, 1].min()) else 1
        lo_a, hi_a = float(pts[:, axis].min()), float(pts[:, axis].max())
        for k, g in enumerate(gnbs):
            frac = (k + 1) / (len(gnbs) + 1)
            # 依「座標範圍」而非「排序索引」分布 —— 可走格點沿走廊分布不均，
            # 用索引分位會讓兩個 gNB 擠在格點最密的那一段（實測相距不到 6 m）
            target = lo_a + frac * (hi_a - lo_a)
            px, pz = pts[np.abs(pts[:, axis] - target).argmin()]
            changes["gnbs"].append({
                "name": g.name,
                "from": [round(g.pos_x, 1), round(g.pos_y, 1), round(g.pos_z, 1)],
                "to": [round(float(px), 2), gnb_h, round(float(pz), 2)],
                "power_dbm": gnb_power,
            })
            if not dry_run:
                g.pos_x, g.pos_y, g.pos_z = float(px), gnb_h, float(pz)
                g.power_dbm = gnb_power
                # gNB 的塔高預設是 pos.y x 4，室內會頂穿天花板 → 明確給高度
                g.target_height_m = gnb_h
                g.save()

        if dry_run:
            return success_response(
                {"name": name, "dry_run": True, "grid": grid.stats(),
                 "path": {k: path[k] for k in ("waypoint_count", "path_length_m")},
                 "changes": changes},
                message="dry run — 未寫入",
            )

        # 存進 MapScene 而不是只塞進這一次的 config —— generator 會在每次
        # build 重新產生 config，不落地就會被下一次 build 蓋回城市尺度
        m.indoor_mode = True
        m.gnb_visual_scale = gnb_visual_scale
        m.save(update_fields=["indoor_mode", "gnb_visual_scale", "updated_at"])

        config = SceneConfigGeneratorService.generate()
        KitBusinessService.push_scene_config(config)
        KitBusinessService.build_scene()
        phy_ok, phy_err = _push_scene_to_physics(m, config)

        log.info("setup_indoor %s: %d UE @ %.1fm, %d gNB @ %.1fm, 可走 %.1f m2",
                 name, len(ues), ue_h, len(gnbs), gnb_h,
                 grid.stats()["walkable_area_m2"])
        return success_response(
            {"name": name, "grid": grid.stats(),
             "path": {k: path[k] for k in ("waypoint_count", "path_length_m")},
             "changes": changes, "gnb_visual_scale": gnb_visual_scale,
             "physics_pushed": phy_ok, "physics_error": phy_err},
            message=(f"已切換為室內尺度:{len(ues)} 個 UE 高 {ue_h} m 沿走廊巡走"
                     f"（路徑 {path['path_length_m']} m，不穿牆）、"
                     f"{len(gnbs)} 個 gNB 掛在 {gnb_h} m（視覺尺寸 x{gnb_visual_scale}）、"
                     f"可走面積 {grid.stats()['walkable_area_m2']} m²"),
        )

    @staticmethod
    @actor
    def list(request):
        _d, error = parse_body(request)
        if error:
            return error
        rows = [_row(m) for m in MapScene.objects.all()]
        return success_response({"maps": rows, "count": len(rows)})

    @staticmethod
    @actor
    def read(request):
        data, error = parse_body(request)
        if error:
            return error
        name = data.get("name")
        if not name:
            return error_response("Missing name", {}, 400)
        try:
            m = MapScene.objects.get(name=name)
        except MapScene.DoesNotExist:
            return error_response(f"Map {name} not found", {}, 404)
        return success_response(_row(m))

    @staticmethod
    @actor
    def apply_to_scene(request):
        """套用地圖 = 成為當前場景的地基:
          1) 清掉原本場景物件(gNB/UE/Building)—「蓋掉原本場景」
          2) 標此地圖 active(其餘取消)—— generate() 會據此輸出 environment
          3) generate()(自動帶 environment + skip_buildings)→ push → build
        之後新增 gNB/UE 是往 table 加 row,再 build 即為「地圖 + 新物件」。
        Body: {name, keep_objects?: bool, hide_ceiling?: bool}
              keep_objects=true 則不清既有 gNB/UE；
              hide_ceiling 預設 true —— 匯入的室內掃描會把天花板收起來，
              否則從外面看只是一個封閉盒子。
        """
        data, error = parse_body(request)
        if error:
            return error
        name = data.get("name")
        if not name:
            return error_response("Missing name", {}, 400)
        keep_objects = bool(data.get("keep_objects", False))
        try:
            m = MapScene.objects.get(name=name)
        except MapScene.DoesNotExist:
            return error_response(f"Map {name} not found", {}, 404)
        if m.status != "ready" or not m.usd_path:
            return error_response(f"Map {name} 尚未 ready(status={m.status})", {}, 409)

        try:
            # 1) 覆蓋語意:清掉原本場景物件(地圖建築由 environment USD 提供)
            BuildingObject.objects.all().delete()
            if not keep_objects:
                GnbConfig.objects.all().delete()
                UeConfig.objects.all().delete()
            # 2) 設此地圖為當前 active
            MapScene.objects.exclude(pk=m.pk).update(active=False)
            m.active = True
            m.save(update_fields=["active", "updated_at"])
            # 3) generate()(現在會自動注入 environment）→ 推 + build
            config = SceneConfigGeneratorService.generate()
            # generator 已依 MapScene.indoor_mode 決定；這裡只處理呼叫端的顯式覆寫
            if config.get("environment") is not None and "hide_ceiling" in data:
                config["environment"]["hide_ceiling"] = bool(data["hide_ceiling"])
            KitBusinessService.push_scene_config(config)
            KitBusinessService.build_scene()
            # 4) 同步把該地圖的 Mitsuba 幾何推給 Physics/Sionna(同一份幾何、同一原點)
            phy_ok, phy_err = _push_scene_to_physics(m, config)
            if not phy_ok:
                log.warning("Map %s: Physics 場景推送失敗(Kit 已更新): %s", name, phy_err)
            log.info("Map %s applied (active) — env=%s keep_objects=%s physics=%s",
                     name, m.usd_path, keep_objects, "ok" if phy_ok else "fail")
            return success_response(
                {"name": name, "usd_path": m.usd_path, "active": True,
                 "gnbs": len(config.get("gnbs", [])),
                 "ues": len(config.get("ues", [])),
                 "physics_pushed": phy_ok, "physics_error": phy_err},
                message=f"地圖 {name} 已套用為當前場景"
                        + ("" if phy_ok else "(Sionna 場景未同步)"),
            )
        except Exception as e:  # noqa: BLE001
            log.exception("apply_to_scene failed for map %s", name)
            return error_response(f"套用失敗:{e}", {}, 500)

    @staticmethod
    @actor
    def plan_path(request):
        """規劃一條繞過建築的 UE 路徑(解決穿牆)。

        Body: {name, from:[x,z], to:[x,z], cell_m?, clearance_m?}
        回傳 waypoints([x,0,z]),可直接餵給 UEController/create 的 waypoints。
        """
        data, error = parse_body(request)
        if error:
            return error
        name = data.get("name")
        if not name:
            return error_response("Missing name", {}, 400)
        try:
            m = MapScene.objects.get(name=name)
        except MapScene.DoesNotExist:
            return error_response(f"Map {name} not found", {}, 404)
        if m.status != "ready" or not m.usd_path:
            return error_response(f"Map {name} 尚未 ready", {}, 409)

        def _xz(key):
            v = data.get(key)
            if not isinstance(v, (list, tuple)) or len(v) < 2:
                raise ValueError(f"{key} 需為 [x, z]")
            return (float(v[0]), float(v[1]))

        try:
            start = _xz("from")
            goal = _xz("to")
        except (ValueError, TypeError) as e:
            return error_response(str(e), {}, 400)

        from main.apps.ran.services.optional.path_planner import (
            PathPlanError, plan_path as _plan,
        )
        try:
            result = _plan(
                m.usd_path, start, goal,
                cell_m=float(data.get("cell_m") or 2.0),
                clearance_m=float(data.get("clearance_m") or 2.0),
            )
        except PathPlanError as e:
            return error_response(str(e), {"name": name}, 422)
        except Exception as e:  # noqa: BLE001
            log.exception("plan_path failed for %s", name)
            return error_response(f"路徑規劃失敗:{e}", {}, 500)

        log.info("plan_path %s: %s → %s, %d waypoints, %.0fm (直線 %.0fm)",
                 name, start, goal, result["waypoint_count"],
                 result["path_length_m"], result["direct_distance_m"])
        return success_response(
            result,
            message=f"路徑規劃完成:{result['waypoint_count']} 個 waypoint、"
                    f"{result['path_length_m']} m",
        )

    @staticmethod
    @actor
    def detach(request):
        """把當前地圖從場景移除(回到無地圖的一般場景),重新 build。"""
        _d, error = parse_body(request)
        if error:
            return error
        try:
            MapScene.objects.filter(active=True).update(active=False)
            config = SceneConfigGeneratorService.generate()
            KitBusinessService.push_scene_config(config)
            KitBusinessService.build_scene()
            return success_response({"active": None}, message="已移除當前地圖")
        except Exception as e:  # noqa: BLE001
            log.exception("detach map failed")
            return error_response(f"移除失敗:{e}", {}, 500)

    @staticmethod
    @actor
    def delete(request):
        data, error = parse_body(request)
        if error:
            return error
        name = data.get("name")
        if not name:
            return error_response("Missing name", {}, 400)
        try:
            m = MapScene.objects.get(name=name)
        except MapScene.DoesNotExist:
            return error_response(f"Map {name} not found", {}, 404)
        if m.usd_path and os.path.exists(m.usd_path):
            try:
                os.remove(m.usd_path)
            except OSError as e:
                log.warning("Failed to delete USD %s: %s", m.usd_path, e)
        stem = os.path.splitext(m.usd_path)[0] if m.usd_path else ""
        for suffix in (".materials.npz", ".materials.json", "_materials.usd",
                       ".mitsuba.xml", ".mitsuba.stats.json"):
            side = stem + suffix
            if stem and os.path.exists(side):
                try:
                    os.remove(side)
                except OSError as e:
                    log.warning("Failed to delete %s: %s", side, e)
        mesh_dir = stem + ".mitsuba_meshes"
        if stem and os.path.isdir(mesh_dir):
            import shutil
            try:
                shutil.rmtree(mesh_dir)
            except OSError as e:
                log.warning("Failed to delete %s: %s", mesh_dir, e)

        glb = _glb_path_for(m.usd_path)
        if glb and os.path.exists(glb):
            try:
                os.remove(glb)
            except OSError as e:
                log.warning("Failed to delete GLB %s: %s", glb, e)
        # GLB 匯入會另外產出一個貼圖資料夾，沒清掉會在 assets/maps 累積數十 MB 孤兒檔
        tex_dir = os.path.splitext(m.usd_path)[0] + "_textures" if m.usd_path else ""
        if tex_dir and os.path.isdir(tex_dir):
            import shutil
            try:
                shutil.rmtree(tex_dir)
            except OSError as e:
                log.warning("Failed to delete textures %s: %s", tex_dir, e)
        m.delete()
        return success_response({"name": name}, message="Map deleted")
