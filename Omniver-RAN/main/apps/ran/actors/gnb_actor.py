from __future__ import annotations

from django.conf import settings

from main.apps.ran.actors._http import actor, parse_body
from main.apps.ran.models import GnbConfig
from main.apps.ran.serializers.gnb_serializers import (
    GnbReadSerializer,
    GnbStateWriteSerializer,
    GnbWriteSerializer,
)
from main.apps.ran.services.business.kit_operations import KitBusinessService
from main.apps.ran.services.business.ranpsim_operations import RanpsimBusinessService
from main.apps.ran.services.business.sqldb_operations import SqlDbBusinessService
from main.apps.ran.services.common.timestamp_service import TimestampService
from main.apps.ran.services.common.uuid_service import UUIDService
from main.utils.logger import get_logger
from main.utils.response import error_response, success_response

log = get_logger(__name__)


class GNBReader:
    @staticmethod
    @actor
    def read(request):  # noqa: ARG004
        try:
            gnbs = SqlDbBusinessService.list_entities(GnbConfig)
            output = [GnbReadSerializer.to_representation(g) for g in gnbs]
            return success_response(output)
        except Exception as e:  # noqa: BLE001
            return error_response("Failed to read gNBs from database", {"detail": str(e)}, 500)


class GNBController:
    @staticmethod
    @actor
    def create(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        s = GnbWriteSerializer(data=data)
        if not s.is_valid():
            return error_response("Validation failed", s.errors, 400)

        v = s.validated_data
        gnb_uuid = UUIDService.generate_uuid("gnb", v["name"])
        ts = TimestampService.get_current_timestamp()

        entity_data = {
            "gnb_uuid": gnb_uuid,
            "gnb_created_at": ts,
            "gnb_updated_at": ts,
            **v,
        }

        gnb = SqlDbBusinessService.create_entity(GnbConfig, entity_data)
        output = GnbReadSerializer.to_representation(gnb)
        return success_response(output, "gNB created", 201)

    @staticmethod
    @actor
    def delete(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        name = data.get("name")
        if not name or not isinstance(name, str):
            return error_response("Validation failed", {"name": "required (str)"}, 400)

        cfg = SqlDbBusinessService.find_entity(GnbConfig, name=name)
        if cfg is None:
            return error_response(f"gNB '{name}' not found", status=404)

        SqlDbBusinessService.delete_entity(cfg)
        return success_response({"name": name}, "gNB deleted")

    @staticmethod
    @actor
    def update(request):
        data, err = parse_body(request)
        if err is not None:
            return err

        name = data.get("name")
        if not name or not isinstance(name, str):
            return error_response("Validation failed", {"name": "required (str)"}, 400)

        cfg = SqlDbBusinessService.find_entity(GnbConfig, name=name)
        if cfg is None:
            return error_response(f"gNB '{name}' not found", status=404)

        s = GnbStateWriteSerializer(data=data)
        # 更新時只允許修改 USD 規範的屬性（position, power_dbm, frequency_ghz, bandwidth_mhz, active, color, target_height_m, cells）
        v = s._validate_update(data)
        if not v:
            return error_response("No editable USD fields provided (allowed: position, power_dbm, frequency_ghz, bandwidth_mhz, active, color, target_height_m, cells)", status=400)

        # ---- DB updates (canonical values for ranp-sim etc.) ----
        updates: dict = {"gnb_updated_at": TimestampService.get_current_timestamp()}
        if v.get("power_dbm") is not None:
            updates["power_dbm"] = v["power_dbm"]
        if v.get("active") is not None:
            updates["active"] = v["active"]
        if v.get("frequency_ghz") is not None:
            updates["freq_mhz"] = float(v["frequency_ghz"]) * 1000.0
        if v.get("bandwidth_mhz") is not None:
            updates["bw_hz"] = float(v["bandwidth_mhz"]) * 1_000_000.0
        if v.get("position") is not None:
            updates["pos_x"] = float(v["position"]["x"])
            updates["pos_y"] = float(v["position"]["y"])
            updates["pos_z"] = float(v["position"]["z"])
        if v.get("color_r") is not None:
            updates["color_r"] = v["color_r"]
        if v.get("color_g") is not None:
            updates["color_g"] = v["color_g"]
        if v.get("color_b") is not None:
            updates["color_b"] = v["color_b"]
        if v.get("target_height_m") is not None:
            updates["target_height_m"] = v["target_height_m"]
        # AK9: cells (per-sector pci + azimuth_deg) — Dashboard 透過 inspector panel
        # 改 sector 方向時，serializer 把這個 array 帶下來，過去 actor 漏寫進 DB
        # 導致前端按 Update 看起來「沒反應」。現在連 JSONField 一起寫入，並讓下游
        # ranp-sim push 拿到最新值。
        if v.get("cells") is not None:
            updates["cells"] = v["cells"]
        SqlDbBusinessService.update_entity(cfg, updates)

        # ---- Kit forward (reflect in viewport + HUD label) ----
        kit_changes: dict = {}
        for k in ("power_dbm", "active", "frequency_ghz", "bandwidth_mhz", "position"):
            if v.get(k) is not None:
                kit_changes[k] = v[k]
        kit_err: str | None = None
        if kit_changes:
            try:
                KitBusinessService.update_gnb(name, kit_changes)
            except Exception as e:  # noqa: BLE001
                # DB already updated; viewport just didn't get the push.
                # Report back so caller knows to retry or inspect.
                log.warning("GNBController.update: Kit push failed for %s: %s", name, e)
                kit_err = str(e)

        # ---- Direct push to ranp-sim (override_mode=ran_only) ----
        # ran_only 整批覆蓋 gNB 列表，所以送所有目前 gNB（已 bake 改動），
        # 不是只送剛改那個，否則其他 gNB 會被刪。
        # 全部從 live GnbConfig 拉(含 cells[])，不再讀 stale SceneSnapshot。
        bridge_err: str | None = None
        bridge_resp = None
        try:
            scene_id, all_gnbs = _build_full_gnb_list_for_bridge()
            if scene_id and all_gnbs:
                bridge_resp = RanpsimBusinessService.push_scene(scene_id, all_gnbs)
        except Exception as e:  # noqa: BLE001
            log.warning("GNBController.update: ranp-sim push failed for %s: %s", name, e)
            bridge_err = str(e)

        payload: dict = {"name": name, "applied": list(kit_changes.keys())}
        if kit_err is not None:
            payload["kit_error"] = kit_err
        if bridge_err is not None:
            payload["bridge_error"] = bridge_err
        elif bridge_resp is not None:
            payload["bridge"] = "pushed"
        return success_response(payload, "updated")


def _build_full_gnb_list_for_bridge() -> tuple[str | None, list[dict]]:
    """Assemble scene_id + complete gNB list for ranp-sim push (ran_only override).

    Flattens GnbConfig.cells[] into per-cell entries — ranp-sim push_scene schema
    is one entry per cell (pci + cell_id + position 各自獨立)。一個 gNB 有 N 個
    cell 就 emit N 個 entry。GnbConfig.cells 空時 fallback 為「單 cell at gNB
    position with pci=0, cell_id={name}_c0」。

    scene_id 走 settings 預設 — 不再讀 stale SceneSnapshot。
    """
    scene_id = getattr(settings, "RANPSIM_SCENE_ID", "umi_3sector_v1")
    out: list[dict] = []
    for g in GnbConfig.objects.all():
        gnb_pos = [float(g.pos_x or 0), float(g.pos_y or 0), float(g.pos_z or 0)]
        freq_ghz = float(g.freq_mhz) / 1000.0 if g.freq_mhz else 3.5
        bw_mhz = float(g.bw_hz) / 1_000_000.0 if g.bw_hz else 100.0
        power_dbm = float(g.power_dbm) if g.power_dbm is not None else 43.0

        cells = g.cells or []
        if not cells:
            cells = [{"pci": 0, "cell_id": f"{g.name}_c0", "position": gnb_pos}]

        for i, c in enumerate(cells):
            cell_id = str(c.get("cell_id") or f"{g.name}_c{i}")
            pci = int(c.get("pci") or 0)
            # cell.position 是 DAS / multi-TRP 物理分離用,沒給就 fallback gNB position
            cpos = c.get("position") or gnb_pos
            out.append({
                "name": g.name,
                "pci": pci,
                "cell_id": cell_id,
                "position": [float(cpos[0]), float(cpos[1]), float(cpos[2])],
                "frequency_ghz": freq_ghz,
                "power_dbm": power_dbm,
                "bandwidth_mhz": bw_mhz,
            })
    if not out:
        return (None, [])
    return (scene_id, out)
