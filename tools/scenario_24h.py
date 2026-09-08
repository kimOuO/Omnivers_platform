"""產生 24 小時的走廊人流劇本（位置 + 流量），輸出成平台的 scenario JSON。

人流的建模方式：**固定的 UE 池 + 每人各自的在場時段**。
劇本 schema 的 ues 是固定清單，沒有「動態生成/消滅」的概念，所以「人變多變少」
用「同時在場的 UE 數量」表達：不在場的 UE 停在走廊外的等候點、流量歸零，
在場的沿走廊走動並產生流量。

排程用貪婪法而非隨機抽樣：逐 5 分鐘比對目標人數，不足就從閒置池叫人進來、
超過就讓最早進來的離開。這樣**產出的人數曲線與目標完全吻合**，可以驗證；
隨機抽樣只能近似，而且每次結果不同。

走動路徑直接用 scan_walkable 的 A* 結果 —— 與 setup_indoor 同一套可走區域，
所以人不會穿牆，也不會走到掃描沒涵蓋的地方。
"""
from __future__ import annotations

import json
import math
from typing import Any

import numpy as np

# 每小時的相對人流（0..1），對應使用者描述的作息
# 00-07 幾乎沒人 / 07-10 陸續進來 / 11-14 最多 / 14-16 變少 / 16-20 又變多 / 21-24 遞減
HOURLY_LOAD = {
    0: 0.02, 1: 0.01, 2: 0.01, 3: 0.01, 4: 0.02, 5: 0.03,
    6: 0.06, 7: 0.15, 8: 0.35, 9: 0.55, 10: 0.70,
    11: 0.90, 12: 1.00, 13: 0.95,
    14: 0.60, 15: 0.45,
    16: 0.55, 17: 0.75, 18: 0.85, 19: 0.80, 20: 0.60,
    21: 0.40, 22: 0.25, 23: 0.10,
}

SLOT_SEC = 300           # 排程解析度：5 分鐘
WALK_SPEED_MPS = 1.25
WAYPOINT_EVERY_SEC = 30  # 在場時每 30 秒一個位置點（驅動端會線性內插）
PAUSE_PROB = 0.18        # 每個路徑點停下來的機率（看手機、講話）

# 流量樣板（dl_kbps, ul_kbps）：走廊使用者以瀏覽/串流為主
TRAFFIC_MODES = [
    ("idle", 60, 20, 0.30),        # 手機在口袋，背景同步
    ("browse", 1200, 250, 0.40),   # 瀏覽、社群
    ("video", 4500, 300, 0.20),    # 影音串流
    ("upload", 800, 2500, 0.10),   # 上傳照片/視訊通話
]


def occupancy_curve(max_ue: int) -> list[int]:
    """每個 5 分鐘時段的目標在場人數。"""
    slots = 24 * 3600 // SLOT_SEC
    out = []
    for s in range(slots):
        t = s * SLOT_SEC
        h = int(t // 3600)
        # 小時之間線性內插，避免整點出現階梯
        frac = (t % 3600) / 3600.0
        a = HOURLY_LOAD[h]
        b = HOURLY_LOAD[(h + 1) % 24]
        out.append(int(round(max_ue * (a + (b - a) * frac))))
    return out


def schedule_sessions(curve: list[int], max_ue: int, rng) -> list[list[tuple[int, int]]]:
    """貪婪排程 → 每個 UE 的在場時段 [(start_sec, end_sec), ...]。

    不足就叫人進來、超過就讓**待最久**的先走（符合「先到先離開」的直覺，
    也避免同一個人一整天都在走廊裡）。
    """
    sessions: list[list[tuple[int, int]]] = [[] for _ in range(max_ue)]
    active: dict[int, int] = {}          # ue_idx -> start_sec
    for s, target in enumerate(curve):
        t = s * SLOT_SEC
        while len(active) < target:
            idle = [i for i in range(max_ue) if i not in active]
            if not idle:
                break
            pick = int(rng.choice(idle))
            active[pick] = t
        while len(active) > target:
            oldest = min(active, key=lambda k: active[k])
            sessions[oldest].append((active.pop(oldest), t))
    end = len(curve) * SLOT_SEC
    for i, st in active.items():
        sessions[i].append((st, end))
    return sessions


def walk_positions(path: list[tuple[float, float]], t0: int, t1: int,
                   height: float, rng) -> list[list[float]]:
    """在 [t0, t1] 之間沿路徑來回走，回傳 [[t, x, y, z], ...]。"""
    if len(path) < 2 or t1 <= t0:
        return []
    # 路徑累積長度，方便用「已走距離」定位
    seg = [math.dist(path[i], path[i + 1]) for i in range(len(path) - 1)]
    total = sum(seg)
    if total < 1e-6:
        return []
    cum = np.concatenate([[0.0], np.cumsum(seg)])

    def at(dist: float) -> tuple[float, float]:
        # 來回：把距離摺疊進 [0, total]
        lap = dist % (2 * total)
        d = lap if lap <= total else 2 * total - lap
        i = int(np.searchsorted(cum, d) - 1)
        i = max(0, min(len(seg) - 1, i))
        f = (d - cum[i]) / max(seg[i], 1e-9)
        return (path[i][0] + (path[i + 1][0] - path[i][0]) * f,
                path[i][1] + (path[i + 1][1] - path[i][1]) * f)

    out: list[list[float]] = []
    dist = float(rng.uniform(0, total))     # 每個人從不同位置開始
    t = t0
    while t <= t1:
        x, z = at(dist)
        out.append([float(t), round(x, 2), height, round(z, 2)])
        if rng.random() < PAUSE_PROB:
            dist += 0.0                     # 停在原地一個間隔
        else:
            dist += WALK_SPEED_MPS * WAYPOINT_EVERY_SEC * float(rng.uniform(0.75, 1.25))
        t += WAYPOINT_EVERY_SEC
    return out


def traffic_for_sessions(sessions: list[tuple[int, int]], rng,
                         step_sec: int = 120) -> list[list[float]]:
    """流量時間軸 [[t, dl_kbps, ul_kbps], ...]。不在場時歸零。"""
    prof: list[list[float]] = [[0.0, 0.0, 0.0]]
    modes = [m[0] for m in TRAFFIC_MODES]
    probs = np.array([m[3] for m in TRAFFIC_MODES], dtype=float)
    probs /= probs.sum()
    for (t0, t1) in sessions:
        t = t0
        while t < t1:
            k = int(rng.choice(len(modes), p=probs))
            _, dl, ul, _ = TRAFFIC_MODES[k]
            # 每段加 ±35% 抖動，避免所有人流量一模一樣
            prof.append([float(t),
                         round(dl * float(rng.uniform(0.65, 1.35)), 1),
                         round(ul * float(rng.uniform(0.65, 1.35)), 1)])
            t += step_sec
        prof.append([float(t1), 0.0, 0.0])   # 離場 → 歸零
    return prof


def build_scenario(
    *,
    scenario_id: str,
    scene_id: str,
    usd_path: str,
    max_ue: int = 12,
    ue_height_m: float = 1.7,
    park_offset_m: float = 25.0,
    gnbs: list[dict[str, Any]] | None = None,
    mitsuba_xml_path: str | None = None,
    tick_ms: int = 500,
    seed: int = 0,
) -> dict[str, Any]:
    """產生完整的 24 小時劇本 JSON。"""
    from main.apps.ran.services.optional.scan_walkable import ScanGrid, plan_scan_path

    rng = np.random.default_rng(seed)
    grid = ScanGrid(usd_path)
    start, goal = grid.extremes_along_length()
    planned = plan_scan_path(grid, start, goal)
    path = [(float(w[0]), float(w[2])) for w in planned["waypoints"]]
    # 等候點：沿走廊軸線往外拉遠，代表「還沒進到這條走廊的人」。
    #
    # 劇本的 UE 清單是固定的，Kit 會為每個 UE 建一個 prim 並存在整整 24 小時 ——
    # 「離場」只能用「停到看不見的地方」表達，人不會真的消失。拉得夠遠有兩個
    # 好處：鏡頭看走廊時不會出現一團站著不動的人；Sionna 那邊他們落在建築外、
    # 收不到訊號，物理上也說得通。
    #
    # 真正的「消失」需要 Kit scene builder 支援逐 tick 的 visibility 通道，
    # 平台目前沒有這個機制。
    ax = path[1][0] - path[0][0]
    az = path[1][1] - path[0][1]
    n = math.hypot(ax, az) or 1.0
    park = (path[0][0] - ax / n * park_offset_m,
            path[0][1] - az / n * park_offset_m)

    curve = occupancy_curve(max_ue)
    sessions = schedule_sessions(curve, max_ue, rng)

    ues, traffic = [], []
    for i in range(max_ue):
        name = f"p{i:02d}"
        positions: list[list[float]] = [[0.0, park[0], ue_height_m, park[1]]]
        for (t0, t1) in sessions[i]:
            # 進場前一刻仍在等候點 → 讓內插不會從場中央「瞬移」
            positions.append([float(max(0, t0 - 1)), park[0], ue_height_m, park[1]])
            positions += walk_positions(path, t0, t1, ue_height_m, rng)
            positions.append([float(t1), park[0], ue_height_m, park[1]])
        positions.append([86400.0, park[0], ue_height_m, park[1]])
        positions.sort(key=lambda q: q[0])

        ues.append({
            "name": name,
            "positions": positions,
            "target_height_m": ue_height_m,
            "speed_mps": WALK_SPEED_MPS,
            "loop": False,
            # 在場時段 [[t0, t1], ...]。驅動端據此切 Kit 的 UE 可見性，
            # 讓「離場」是真的消失而不是站在遠處。
            "active": [[float(a), float(b)] for (a, b) in sessions[i]],
        })
        traffic.append({"ue_name": name, "profile": traffic_for_sessions(sessions[i], rng)})

    achieved = []
    for s in range(len(curve)):
        t = s * SLOT_SEC
        achieved.append(sum(1 for ss in sessions for (a, b) in ss if a <= t < b))

    return {
        "scenario_id": scenario_id,
        "scene_id": scene_id,
        "duration_sec": 86400.0,
        "tick_ms": tick_ms,
        "ues": ues,
        "gnbs": gnbs or [],
        "buildings": [],
        # 掃描類場景的幾何是 Mitsuba mesh 檔，不是 building 方塊。沒有這個欄位的話，
        # precompute 會用「buildings 方塊」重建幾何 —— buildings 是空的，
        # 整條走廊會被清成自由空間，算出來的 channel 完全不是室內。
        "geometry_source": ({"type": "mitsuba_xml_path", "path": mitsuba_xml_path}
                            if mitsuba_xml_path else None),
        "traffic": traffic,
        "_doc": [
            "24 小時走廊人流劇本（位置 + 流量）",
            f"UE 池 {max_ue} 人，同時在場人數依作息變化：",
            "  00-07 幾乎無人 / 07-10 陸續進來 / 11-14 尖峰 / 14-16 午後減少",
            "  16-20 再次增加 / 21-24 遞減",
            "不在場的人停在走廊外的等候點、流量歸零；在場的沿 A* 路徑來回走動。",
            "路徑取自 scan_walkable 的可走區域，與 setup_indoor 同一套，不會穿牆。",
        ],
        "_metadata": {
            "generator": "tools/scenario_24h.py",
            "max_ue": max_ue,
            "park_point": [round(park[0], 2), round(park[1], 2)],
            "park_offset_m": park_offset_m,
            "visibility": (
                "每個 UE 帶 active 時間軸。呼叫 "
                "RAN/Scenario/ScenarioController/apply_time {scenario_id, t_sec} "
                "會依該時刻切 Kit 的 UE 可見性，離場的人會真的消失。"
                "未套用可見性時，離場的人停在 park_point（走廊外），"
                "且 RAN 模擬中仍會 attach（流量為 0）。"
            ),
            "slot_sec": SLOT_SEC,
            "walk_speed_mps": WALK_SPEED_MPS,
            "path_length_m": planned["path_length_m"],
            "walkable_area_m2": grid.stats()["walkable_area_m2"],
            "target_curve": curve,
            "achieved_curve": achieved,
            "sessions_per_ue": [len(s) for s in sessions],
        },
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/app")
    sc = build_scenario(
        scenario_id="corridor_24h",
        scene_id="scan_20260906",
        usd_path="/home/mitlab/XAPP_DT/Omnivers_platform/assets/maps/scan_20260906.usd",
        mitsuba_xml_path="/home/mitlab/XAPP_DT/Omnivers_platform/assets/maps/scan_20260906.mitsuba.xml",
        max_ue=18,
        gnbs=[
            {"name": "src", "pci": 0, "cell_id": "src", "position": [3.73, 2.5, -14.15],
             "frequency_ghz": 3.5, "power_dbm": 10.0, "bandwidth_mhz": 40.0},
            {"name": "nbr", "pci": 1, "cell_id": "nbr", "position": [1.23, 2.5, 28.10],
             "frequency_ghz": 3.5, "power_dbm": 10.0, "bandwidth_mhz": 40.0},
        ],
    )
    out = "/tmp/corridor_24h.json"
    with open(out, "w") as f:
        json.dump(sc, f, ensure_ascii=False)
    m = sc["_metadata"]
    import os
    print(f"{out}  {os.path.getsize(out)/1e6:.1f} MB")
    print(f"UE {len(sc['ues'])} 人 | 路徑 {m['path_length_m']} m | 可走 {m['walkable_area_m2']} m²")
    print(f"位置點總數 {sum(len(u['positions']) for u in sc['ues'])}")
    print(f"流量斷點總數 {sum(len(t['profile']) for t in sc['traffic'])}")
    tc, ac = m["target_curve"], m["achieved_curve"]
    print(f"人數曲線吻合: {'完全一致' if tc == ac else '有誤差 %d 個時段' % sum(1 for a,b in zip(tc,ac) if a!=b)}")
    for h in range(0, 24, 2):
        s = h * 3600 // SLOT_SEC
        print(f"  {h:02d}:00  目標 {tc[s]:2d} 人  實際 {ac[s]:2d} 人")


def slice_scenario(sc: dict[str, Any], t0: float, t1: float,
                   scenario_id: str) -> dict[str, Any]:
    """從既有劇本切出 [t0, t1) 的時段，時間軸重新基準化到 0。

    precompute 是逐 tick 呼叫 Sionna，24 小時 = 172,800 個 tick。
    先切一小段驗證整條鏈路，比直接投入十幾小時 GPU 合理。
    """
    dur = t1 - t0

    def clip_series(rows: list[list[float]], keep_cols: int) -> list[list[float]]:
        """裁切帶時戳的序列，並在邊界補上內插點，避免開頭/結尾缺值。"""
        out = []
        prev = None
        for r in rows:
            t = r[0]
            if t < t0:
                prev = r
                continue
            if t >= t1:
                break
            if not out and prev is not None:
                out.append([0.0] + list(prev[1:1 + keep_cols]))
            out.append([round(t - t0, 3)] + list(r[1:1 + keep_cols]))
        if not out:
            base = prev if prev is not None else rows[0]
            out = [[0.0] + list(base[1:1 + keep_cols])]
        if out[-1][0] < dur:
            out.append([dur] + list(out[-1][1:]))
        return out

    ues, traffic = [], []
    for u in sc["ues"]:
        pos = clip_series(u["positions"], 3)
        active = []
        for a, b in (u.get("active") or []):
            lo, hi = max(a, t0), min(b, t1)
            if hi > lo:
                active.append([round(lo - t0, 3), round(hi - t0, 3)])
        ues.append({**u, "positions": pos, "active": active})
    for t in sc.get("traffic", []):
        traffic.append({**t, "profile": clip_series(t["profile"], 2)})

    return {**sc,
            "scenario_id": scenario_id,
            "duration_sec": float(dur),
            "ues": ues,
            "traffic": traffic,
            "_doc": [f"自 {sc['scenario_id']} 切出 {t0/3600:.0f}:00–{t1/3600:.0f}:00 的時段"]
                    + list(sc.get("_doc", [])),
            "_metadata": {**sc.get("_metadata", {}),
                          "sliced_from": sc["scenario_id"],
                          "slice_window_sec": [t0, t1]}}
