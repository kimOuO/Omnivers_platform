"""UE 路徑規劃 — 在地圖建築之間找一條 A→B 的無碰撞路徑。

解決「UE 穿牆」:只指定起點/終點,由 A* 在建築佔用格圖上搜尋，
再把路徑平滑成少數 waypoints 餵給 UE(UE 容器維持線性內插，不需改動)。

座標系與地圖/UE 一致:x=東、z=南、單位公尺、原點 = bbox 中心。

流程
  1. 讀 {map}.footprints.json → shapely 多邊形
  2. 建築外擴 clearance(避免路徑貼牆擦過)→ 光柵化成佔用格
  3. 起/終點若落在建築內 → BFS 吸附到最近空格
  4. A*(8 方向)搜最短無碰撞路徑
  5. 視線平滑:兩點直線不穿建築就砍掉中間點(去鋸齒)
"""
from __future__ import annotations

import heapq
import json
import math
from collections import deque
from pathlib import Path
from typing import Any

from shapely import STRtree
from shapely.geometry import LineString, Point, Polygon
from shapely.prepared import prep

DEFAULT_CELL_M = 2.0        # 格點解析度
DEFAULT_CLEARANCE_M = 2.0   # 建築外擴(UE 與牆的最小距離)
GRID_MARGIN_M = 30.0        # 格圖比建築範圍外擴多少(讓路徑能繞到外圍)
MAX_CELLS = 600_000         # 安全上限,避免超大地圖爆記憶體


class PathPlanError(RuntimeError):
    pass


def load_footprints(usd_path: str) -> list[Polygon]:
    """從地圖的 footprints.json 載入建築多邊形(與 USD 同名)。"""
    fp = Path(str(usd_path)).with_suffix(".footprints.json")
    if not fp.exists():
        raise PathPlanError(
            f"找不到建築輪廓檔(需重新產生地圖):{fp}"
        )
    data = json.loads(fp.read_text(encoding="utf-8"))
    polys: list[Polygon] = []
    for f in data:
        pts = f.get("points") or []
        if len(pts) < 4:
            continue
        try:
            p = Polygon(pts)
            if not p.is_valid:
                p = p.buffer(0)
            if p.is_valid and not p.is_empty and p.geom_type == "Polygon":
                polys.append(p)
        except Exception:  # noqa: BLE001
            continue
    if not polys:
        raise PathPlanError("建築輪廓檔沒有有效多邊形")
    return polys


class _Grid:
    """建築佔用格圖 + 座標轉換。"""

    def __init__(self, polys: list[Polygon], cell: float, clearance: float):
        self.cell = float(cell)
        # 外擴後的建築(路徑不可進入)
        self.blocked = [p.buffer(clearance) for p in polys]
        self.tree = STRtree(self.blocked)
        self._prepared = [prep(b) for b in self.blocked]

        xs = [b.bounds[0] for b in self.blocked] + [b.bounds[2] for b in self.blocked]
        zs = [b.bounds[1] for b in self.blocked] + [b.bounds[3] for b in self.blocked]
        self.x0 = min(xs) - GRID_MARGIN_M
        self.z0 = min(zs) - GRID_MARGIN_M
        x1 = max(xs) + GRID_MARGIN_M
        z1 = max(zs) + GRID_MARGIN_M
        self.nx = max(1, int(math.ceil((x1 - self.x0) / self.cell)))
        self.nz = max(1, int(math.ceil((z1 - self.z0) / self.cell)))
        if self.nx * self.nz > MAX_CELLS:
            raise PathPlanError(
                f"格圖過大({self.nx}x{self.nz});請加大 cell_m"
            )
        self.occ = bytearray(self.nx * self.nz)   # 0=free 1=blocked
        self._rasterize()

    # --- 座標轉換 ---
    def to_cell(self, x: float, z: float) -> tuple[int, int]:
        i = int((x - self.x0) / self.cell)
        j = int((z - self.z0) / self.cell)
        return max(0, min(self.nx - 1, i)), max(0, min(self.nz - 1, j))

    def to_world(self, i: int, j: int) -> tuple[float, float]:
        return self.x0 + (i + 0.5) * self.cell, self.z0 + (j + 0.5) * self.cell

    def is_blocked(self, i: int, j: int) -> bool:
        return bool(self.occ[j * self.nx + i])

    def _rasterize(self) -> None:
        """只掃每棟建築的 bbox 範圍內的格子(遠比全圖掃描快)。"""
        for poly, pp in zip(self.blocked, self._prepared):
            minx, minz, maxx, maxz = poly.bounds
            i0, j0 = self.to_cell(minx, minz)
            i1, j1 = self.to_cell(maxx, maxz)
            for j in range(j0, j1 + 1):
                base = j * self.nx
                for i in range(i0, i1 + 1):
                    if self.occ[base + i]:
                        continue
                    cx, cz = self.to_world(i, j)
                    if pp.intersects(Point(cx, cz)):
                        self.occ[base + i] = 1

    def nearest_free(self, i: int, j: int, max_radius_cells: int = 60) -> tuple[int, int]:
        """起/終點落在建築內時,BFS 找最近的空格。"""
        if not self.is_blocked(i, j):
            return i, j
        seen = {(i, j)}
        q = deque([(i, j, 0)])
        while q:
            ci, cj, d = q.popleft()
            if d > max_radius_cells:
                break
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = ci + di, cj + dj
                if not (0 <= ni < self.nx and 0 <= nj < self.nz):
                    continue
                if (ni, nj) in seen:
                    continue
                seen.add((ni, nj))
                if not self.is_blocked(ni, nj):
                    return ni, nj
                q.append((ni, nj, d + 1))
        raise PathPlanError("起點或終點被建築包圍,附近找不到可行位置")

    def segment_blocked(self, p: tuple[float, float], q: tuple[float, float]) -> bool:
        """兩點直線是否穿過任何建築(給平滑用)。"""
        line = LineString([p, q])
        for idx in self.tree.query(line):
            if self._prepared[int(idx)].intersects(line):
                return True
        return False


_NEIGHBORS = [
    (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
    (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)),
    (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2)),
]


def _astar(grid: _Grid, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
    """8 方向 A*,歐氏距離 heuristic。回傳格點路徑。"""
    if start == goal:
        return [start]
    nx = grid.nx

    def h(i: int, j: int) -> float:
        return math.hypot(i - goal[0], j - goal[1])

    open_heap: list[tuple[float, int, tuple[int, int]]] = []
    heapq.heappush(open_heap, (h(*start), 0, start))
    came: dict[tuple[int, int], tuple[int, int]] = {}
    gscore: dict[tuple[int, int], float] = {start: 0.0}
    closed: set[tuple[int, int]] = set()
    counter = 0

    while open_heap:
        _f, _c, cur = heapq.heappop(open_heap)
        if cur in closed:
            continue
        if cur == goal:
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            return path[::-1]
        closed.add(cur)
        ci, cj = cur
        for di, dj, cost in _NEIGHBORS:
            ni, nj = ci + di, cj + dj
            if not (0 <= ni < nx and 0 <= nj < grid.nz):
                continue
            if grid.is_blocked(ni, nj):
                continue
            # 斜走時避免從兩棟建築的對角縫隙鑽過去
            if di and dj and (grid.is_blocked(ci + di, cj) or grid.is_blocked(ci, cj + dj)):
                continue
            nxt = (ni, nj)
            if nxt in closed:
                continue
            ng = gscore[cur] + cost
            if ng < gscore.get(nxt, float("inf")):
                gscore[nxt] = ng
                came[nxt] = cur
                counter += 1
                heapq.heappush(open_heap, (ng + h(ni, nj), counter, nxt))
    raise PathPlanError("找不到可通行路徑(起終點之間可能被建築完全阻隔)")


def _smooth(grid: _Grid, pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """視線平滑:能直達的就跳過中間點,去掉格點鋸齒。"""
    if len(pts) <= 2:
        return pts
    out = [pts[0]]
    i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and grid.segment_blocked(pts[i], pts[j]):
            j -= 1
        out.append(pts[j])
        i = j
    return out


def plan_path(
    usd_path: str,
    start_xz: tuple[float, float],
    goal_xz: tuple[float, float],
    cell_m: float = DEFAULT_CELL_M,
    clearance_m: float = DEFAULT_CLEARANCE_M,
) -> dict[str, Any]:
    """規劃 A→B 的無碰撞路徑。回傳 waypoints([x, 0, z])與統計。"""
    polys = load_footprints(usd_path)
    grid = _Grid(polys, cell_m, clearance_m)

    si, sj = grid.to_cell(*start_xz)
    gi, gj = grid.to_cell(*goal_xz)
    s_snapped = grid.is_blocked(si, sj)
    g_snapped = grid.is_blocked(gi, gj)
    si, sj = grid.nearest_free(si, sj)
    gi, gj = grid.nearest_free(gi, gj)

    cells = _astar(grid, (si, sj), (gi, gj))
    raw = [grid.to_world(i, j) for i, j in cells]
    pts = _smooth(grid, raw)

    length = sum(
        math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1)
    )
    direct = math.dist(start_xz, goal_xz)
    return {
        "waypoints": [[round(x, 2), 0.0, round(z, 2)] for x, z in pts],
        "waypoint_count": len(pts),
        "path_length_m": round(length, 1),
        "direct_distance_m": round(direct, 1),
        "detour_ratio": round(length / direct, 2) if direct > 0.01 else 1.0,
        "grid": {"nx": grid.nx, "nz": grid.nz, "cell_m": cell_m,
                 "clearance_m": clearance_m},
        "start_snapped": s_snapped,   # 起點原本在建築內,已移到最近空地
        "goal_snapped": g_snapped,
        "buildings": len(polys),
    }
