"""從室內掃描 USD 算出「人走得到的地方」，並在上面規劃不穿牆的路徑。

為什麼不用 `path_planner.py`：那支吃的是 OSM footprint 多邊形（shapely），
掃描模型沒有 footprint，只有一坨三角形。這裡改成直接把三角形柵格化成
佔用格圖，但**格圖介面刻意做成與 `path_planner._Grid` 相同**
（to_cell / to_world / is_blocked / nearest_free / segment_blocked），
所以 A* 與路徑平滑可以原封不動重用，不必再寫一份。

判斷「可走」用三個高度帶，缺一不可：
  - 地板帶（y≈0）有面 → 這一格底下真的有地板，可以站人。
    這一刀同時把「模型外面」排除掉 —— 走廊外沒有掃到地板，自然不可走。
  - 身體帶（0.35–1.9 m）沒有面 → 沒有牆、柱子、家具擋路。
  - 再對身體帶做形態學膨脹，留出肩寬 clearance，避免路徑貼著牆走。

座標直接讀轉好的 USD，與 Kit 顯示、Mitsuba 給 Sionna 的幾何同一個原點。
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from main.apps.ran.services.optional.path_planner import _astar, _smooth

# 預設值：0.25 m 一格對走廊尺度夠細，人的肩寬留 0.35 m
DEFAULT_CELL_M = 0.25
DEFAULT_CLEARANCE_M = 0.35
FLOOR_BAND = (-0.45, 0.35)   # 地板帶（相對 y=0，容許掃描起伏）
BODY_BAND = (0.35, 1.90)     # 身體帶：這個高度有東西就走不過去
MAX_CELLS = 400_000


class WalkableError(RuntimeError):
    pass


def load_usd_triangles(usd_path: str) -> tuple[np.ndarray, np.ndarray]:
    """讀 USD 內所有 Mesh 的世界座標三角形。"""
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(usd_path)
    if stage is None:
        raise WalkableError(f"無法開啟 USD: {usd_path}")

    all_pts: list[np.ndarray] = []
    all_tris: list[np.ndarray] = []
    offset = 0
    xform_cache = UsdGeom.XformCache()
    for prim in stage.Traverse():
        if prim.GetTypeName() != "Mesh":
            continue
        mesh = UsdGeom.Mesh(prim)
        pts = np.asarray(mesh.GetPointsAttr().Get() or [], dtype=np.float64)
        idx = np.asarray(mesh.GetFaceVertexIndicesAttr().Get() or [], dtype=np.int64)
        counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get() or [], dtype=np.int64)
        if not len(pts) or not len(idx) or not len(counts):
            continue
        if not np.all(counts == 3):
            continue   # 匯入的掃描一律三角化，非三角面直接略過
        m = np.asarray(xform_cache.GetLocalToWorldTransform(prim), dtype=np.float64)
        pts = (np.hstack([pts, np.ones((len(pts), 1))]) @ m)[:, :3]
        all_pts.append(pts)
        all_tris.append(idx.reshape(-1, 3) + offset)
        offset += len(pts)

    if not all_pts:
        raise WalkableError(f"USD 內沒有三角網格: {usd_path}")
    return np.vstack(all_pts), np.vstack(all_tris)


def _mark_bbox(occ: np.ndarray, pts: np.ndarray, tris: np.ndarray,
               x0: float, z0: float, cell: float) -> None:
    """把三角形在 XZ 平面的 bbox 塗進格圖。

    用 bbox 而非精確覆蓋是刻意的：牆是很薄的面，精確柵格化容易在薄牆上留下
    沒被標記的縫，路徑就會從那個縫「鑽牆」過去。bbox 偏保守，寧可多擋。
    """
    if not len(tris):
        return
    v = pts[tris]
    lo = v.min(axis=1)
    hi = v.max(axis=1)
    nx, nz = occ.shape
    i0 = np.clip(((lo[:, 0] - x0) / cell).astype(np.int64), 0, nx - 1)
    i1 = np.clip(((hi[:, 0] - x0) / cell).astype(np.int64), 0, nx - 1)
    j0 = np.clip(((lo[:, 2] - z0) / cell).astype(np.int64), 0, nz - 1)
    j1 = np.clip(((hi[:, 2] - z0) / cell).astype(np.int64), 0, nz - 1)
    for a, b, c, d in zip(i0, i1, j0, j1):
        occ[a:b + 1, c:d + 1] = True


def _dilate(mask: np.ndarray, radius_cells: int) -> np.ndarray:
    """簡易方形膨脹（留 clearance）。用位移疊加，不引入 scipy。"""
    if radius_cells <= 0:
        return mask
    out = mask.copy()
    for di in range(-radius_cells, radius_cells + 1):
        for dj in range(-radius_cells, radius_cells + 1):
            if di == 0 and dj == 0:
                continue
            shifted = np.zeros_like(mask)
            si = slice(max(0, di), mask.shape[0] + min(0, di))
            ti = slice(max(0, -di), mask.shape[0] + min(0, -di))
            sj = slice(max(0, dj), mask.shape[1] + min(0, dj))
            tj = slice(max(0, -dj), mask.shape[1] + min(0, -dj))
            shifted[ti, tj] = mask[si, sj]
            out |= shifted
    return out


def _largest_component(walkable: np.ndarray) -> np.ndarray:
    """只保留最大的連通可走區域，濾掉牆縫裡的孤立假空間。"""
    nx, nz = walkable.shape
    seen = np.zeros_like(walkable)
    best: list[tuple[int, int]] = []
    for si in range(nx):
        for sj in range(nz):
            if not walkable[si, sj] or seen[si, sj]:
                continue
            comp = []
            stack = [(si, sj)]
            seen[si, sj] = True
            while stack:
                i, j = stack.pop()
                comp.append((i, j))
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = i + di, j + dj
                    if 0 <= a < nx and 0 <= b < nz and walkable[a, b] and not seen[a, b]:
                        seen[a, b] = True
                        stack.append((a, b))
            if len(comp) > len(best):
                best = comp
    out = np.zeros_like(walkable)
    for i, j in best:
        out[i, j] = True
    return out


class ScanGrid:
    """掃描幾何的可走格圖。介面與 `path_planner._Grid` 相同，可直接餵給 `_astar`。"""

    def __init__(self, usd_path: str, cell: float = DEFAULT_CELL_M,
                 clearance: float = DEFAULT_CLEARANCE_M,
                 floor_band: tuple[float, float] = FLOOR_BAND,
                 body_band: tuple[float, float] = BODY_BAND):
        self.cell = float(cell)
        pts, tris = load_usd_triangles(usd_path)

        lo = pts.min(axis=0)
        hi = pts.max(axis=0)
        self.x0, self.z0 = float(lo[0]), float(lo[2])
        self.nx = max(1, int(math.ceil((hi[0] - lo[0]) / self.cell)) + 1)
        self.nz = max(1, int(math.ceil((hi[2] - lo[2]) / self.cell)) + 1)
        if self.nx * self.nz > MAX_CELLS:
            raise WalkableError(f"格圖過大({self.nx}x{self.nz})；請加大 cell_m")

        cy = pts[tris][:, :, 1].mean(axis=1)
        floor_mask = (cy >= floor_band[0]) & (cy <= floor_band[1])
        body_mask = (cy > body_band[0]) & (cy <= body_band[1])

        has_floor = np.zeros((self.nx, self.nz), dtype=bool)
        blocked = np.zeros((self.nx, self.nz), dtype=bool)
        _mark_bbox(has_floor, pts, tris[floor_mask], self.x0, self.z0, self.cell)
        _mark_bbox(blocked, pts, tris[body_mask], self.x0, self.z0, self.cell)

        self.blocked_raw = blocked
        self.has_floor = has_floor
        dilated = _dilate(blocked, int(round(clearance / self.cell)))
        self.walkable = _largest_component(has_floor & ~dilated)
        self.clearance = float(clearance)

    # --- path_planner._Grid 相容介面 ---
    def to_cell(self, x: float, z: float) -> tuple[int, int]:
        i = int((x - self.x0) / self.cell)
        j = int((z - self.z0) / self.cell)
        return max(0, min(self.nx - 1, i)), max(0, min(self.nz - 1, j))

    def to_world(self, i: int, j: int) -> tuple[float, float]:
        return self.x0 + (i + 0.5) * self.cell, self.z0 + (j + 0.5) * self.cell

    def is_blocked(self, i: int, j: int) -> bool:
        return not bool(self.walkable[i, j])

    def nearest_free(self, i: int, j: int, max_radius_cells: int = 120) -> tuple[int, int]:
        if not self.is_blocked(i, j):
            return i, j
        for r in range(1, max_radius_cells + 1):
            for di in range(-r, r + 1):
                for dj in (-r, r):
                    a, b = i + di, j + dj
                    if 0 <= a < self.nx and 0 <= b < self.nz and not self.is_blocked(a, b):
                        return a, b
            for dj in range(-r, r + 1):
                for di in (-r, r):
                    a, b = i + di, j + dj
                    if 0 <= a < self.nx and 0 <= b < self.nz and not self.is_blocked(a, b):
                        return a, b
        raise WalkableError("找不到可走格點（掃描內沒有可站立空間？）")

    def segment_blocked(self, p: tuple[float, float], q: tuple[float, float]) -> bool:
        """線段是否穿過不可走區域 —— `_smooth` 用它拉直路徑。

        以半格為間距取樣：比格子細，才不會讓路徑「跳過」一格薄牆。
        """
        d = math.dist(p, q)
        steps = max(2, int(d / (self.cell * 0.5)))
        for k in range(steps + 1):
            t = k / steps
            x = p[0] + (q[0] - p[0]) * t
            z = p[1] + (q[1] - p[1]) * t
            if self.is_blocked(*self.to_cell(x, z)):
                return True
        return False

    # --- 統計 / 取樣 ---
    def stats(self) -> dict[str, Any]:
        total = self.nx * self.nz
        return {
            "nx": self.nx, "nz": self.nz, "cell_m": self.cell,
            "clearance_m": self.clearance,
            "floor_cells": int(self.has_floor.sum()),
            "blocked_cells": int(self.blocked_raw.sum()),
            "walkable_cells": int(self.walkable.sum()),
            "walkable_area_m2": round(float(self.walkable.sum()) * self.cell ** 2, 1),
            "walkable_pct": round(100.0 * float(self.walkable.sum()) / total, 1),
            "bounds": {"x": [round(self.x0, 2), round(self.x0 + self.nx * self.cell, 2)],
                       "z": [round(self.z0, 2), round(self.z0 + self.nz * self.cell, 2)]},
        }

    def walkable_points(self) -> np.ndarray:
        """所有可走格點的世界座標 (n, 2)。"""
        idx = np.argwhere(self.walkable)
        return np.column_stack([
            self.x0 + (idx[:, 0] + 0.5) * self.cell,
            self.z0 + (idx[:, 1] + 0.5) * self.cell,
        ])

    def extremes_along_length(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """可走區域在長軸兩端的代表點 —— 拿來當來回巡走的起訖。"""
        pts = self.walkable_points()
        if not len(pts):
            raise WalkableError("沒有可走區域")
        span_x = pts[:, 0].max() - pts[:, 0].min()
        span_z = pts[:, 1].max() - pts[:, 1].min()
        axis = 0 if span_x >= span_z else 1
        lo = pts[pts[:, axis].argmin()]
        hi = pts[pts[:, axis].argmax()]
        return (float(lo[0]), float(lo[1])), (float(hi[0]), float(hi[1]))


def plan_scan_path(grid: ScanGrid, start_xz: tuple[float, float],
                   goal_xz: tuple[float, float]) -> dict[str, Any]:
    """在掃描格圖上規劃不穿牆的路徑，回傳與 `path_planner.plan_path` 同形狀的結果。"""
    si, sj = grid.to_cell(*start_xz)
    gi, gj = grid.to_cell(*goal_xz)
    s_snapped = grid.is_blocked(si, sj)
    g_snapped = grid.is_blocked(gi, gj)
    si, sj = grid.nearest_free(si, sj)
    gi, gj = grid.nearest_free(gi, gj)

    cells = _astar(grid, (si, sj), (gi, gj))
    if not cells:
        raise WalkableError("A* 找不到路徑（起訖點可能不在同一個連通空間）")
    raw = [grid.to_world(i, j) for i, j in cells]
    pts = _smooth(grid, raw)
    length = sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1))
    return {
        "waypoints": [[round(x, 2), 0.0, round(z, 2)] for x, z in pts],
        "waypoint_count": len(pts),
        "path_length_m": round(length, 1),
        "start_snapped": s_snapped,
        "goal_snapped": g_snapped,
    }
