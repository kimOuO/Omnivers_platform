"""掃描網格 → radio material 分類（給 Sionna 用）。

問題：photogrammetry 產出的 GLB，material 是貼圖 atlas 的分塊（名稱是 MD5），
不帶任何語意。但 Sionna 依 BSDF id 判定 radio material，需要 mesh 先按
`itu_concrete / itu_wood / itu_glass / itu_metal / itu_brick` 分群。

做法：逐三角形取「貼圖色彩 + 幾何朝向 + 高度」三個特徵做規則式分類。
純色彩分類誤判率高（照片受光影影響大，白牆／玻璃／金屬在 HSV 上很接近），
所以**先用幾何把候選範圍砍掉**再看顏色：

  - 水平面（地板／天花）→ 一律 concrete。室內不會有朝上的木門或玻璃，
    這一刀就免掉了整類誤判（實測佔 31% 面積）。
  - 斜面（掃描雜訊、家具邊緣、轉角）→ 一律 concrete。這些面本來就不可信。
  - 只有垂直面（53% 面積）才進色彩規則，判 wood / glass / metal / concrete。

規則跑完後還會做一次**連通分量清理**：真實的門、窗是連成一片的，而誤判多半
是散落的單面雜點。小於門檻面積的非混凝土色塊一律退回 concrete
（v1 未做時 metal 分出 1417 群、其中只有 4 群 ≥1 m²，等於全是雜訊）。

分類結果會落地成 .npz（逐面標籤）+ .json（人可讀的統計與當次門檻），
之後產生 Mitsuba 場景時直接讀，不用每次重跑；門檻調整過也能從 json 對照。

## v3 的關鍵改動：只判「能證明的」，其餘棄權

v2 用色彩判 glass / metal，實測**全是誤判**（詳見
`plan/scan_material_report.md` 與 `.claude/skills/scan-material-classification/`）：

  - 三者的色相幾乎相同（concrete 60.0°、glass 57.4°、metal 61.5°），
    規則實際上只剩「很亮 + 沒顏色」，而室內 71.5% 的垂直面 S<0.15、
    22.1% 的 V>0.85 —— 白牆、白門框、反光桌面全都滿足。
  - 根本原因是物理的：**玻璃透明、金屬鏡面，它們在照片裡的外觀不是自己的
    性質**，而是背後與周圍的東西。沒有固有反照率可拍，就沒有色彩特徵可判。
  - wood 相反：不透明 + 漫反射 + 色相集中在 6° 的窄帶、飽和度 0.61，
    是**肯定式特徵**，只有 12.7% 的垂直面落在帶內 → 判得準。

所以 v3 預設 `mode="conservative"`：concrete + wood，其餘標為 UNKNOWN 並
**保守回退成不透明的 concrete**。做覆蓋/隔離度時，把牆誤判成玻璃（訊號穿過去）
遠比把玻璃誤判成牆嚴重，回退方向必須偏向不透明。

輸出一律附上 `evidence`：有正面證據支持的面積佔比、以及回退面積佔比。
「4.4% 是玻璃」而不說那 4.4% 的信心是零，比不分類更危險。
"""
from __future__ import annotations

import colorsys
import json
from pathlib import Path
from typing import Any

import numpy as np

from main.apps.ran.services.optional.glb_to_usd import (
    GlbError,
    estimate_floor_y,
    iter_mesh_instances,
    parse_glb,
    read_accessor,
    _material_image,
    _normalize_uv,
    _view_bytes,
)

# 規則版本 —— 門檻調整後請 +1，落地的 json 會記錄，方便回溯是哪一版分出來的
RULESET_VERSION = 4

LABELS = ["itu_concrete", "itu_wood", "itu_glass", "itu_metal"]
LABEL_IDX = {name: i for i, name in enumerate(LABELS)}

# 預覽用顏色（寫進 USD 的 displayColor，方便在 Kit 裡目視檢查分類對不對）
PREVIEW_COLOR = {
    "itu_concrete": (0.72, 0.72, 0.70),
    "itu_wood": (0.55, 0.31, 0.12),
    "itu_glass": (0.25, 0.65, 0.85),
    "itu_metal": (0.85, 0.30, 0.75),
}

# ── 幾何門檻 ───────────────────────────────────────────────
HORIZONTAL_DEG = 60.0   # 與水平面夾角 > 此值 → 視為地板/天花
VERTICAL_DEG = 30.0     # 與水平面夾角 < 此值 → 視為牆面（可進色彩規則）

# ── 色彩門檻（HSV，H 以度為單位）────────────────────────────
WOOD_HUE = (12.0, 48.0)     # 木頭的橙褐色相帶
WOOD_SAT_MIN = 0.22         # 飽和度不夠就只是暖色調的白牆
WOOD_VAL = (0.12, 0.78)     # 太亮的橙 = 反光，不是木頭本色

GLASS_VAL_MIN = 0.90        # 窗戶在照片裡多半過曝成一片白
GLASS_SAT_MAX = 0.14
GLASS_HEIGHT_MIN_M = 0.8    # 低於這個高度的亮面比較可能是反光地面/踢腳板

METAL_SAT_MAX = 0.10        # 金屬（電梯門、門框）：低飽和 + 中高亮度
METAL_VAL = (0.55, 0.88)
METAL_STD_MIN = 0.04        # 金屬表面有鏡面漸層 → 取樣點之間變異較大，純白牆則平坦

# 連通分量清理：小於此面積的非混凝土色塊視為誤判，退回 concrete。
# 0.3 m² 約是半扇門的 1/6，真實的門窗不會小於這個尺度。
MIN_PATCH_AREA_M2 = 0.3


def _sample_texture(img: np.ndarray, uv: np.ndarray) -> np.ndarray:
    """以 UV 取樣貼圖，回傳 (n, 3) 的 0..1 RGB。UV 依 glTF 慣例 wrap。"""
    h, w = img.shape[:2]
    u = np.mod(uv[:, 0], 1.0)
    v = np.mod(uv[:, 1], 1.0)
    px = np.clip((u * w).astype(np.int64), 0, w - 1)
    # glTF 的 v 原點在上 → 直接乘高度即為列索引
    py = np.clip((v * h).astype(np.int64), 0, h - 1)
    return img[py, px, :3].astype(np.float32) / 255.0


def _rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    """(n,3) RGB 0..1 → (n,3) HSV，H 為度數。colorsys 是純量版，這裡自己向量化。"""
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    mx = rgb.max(axis=1)
    mn = rgb.min(axis=1)
    diff = mx - mn
    h = np.zeros_like(mx)
    mask = diff > 1e-6
    idx = (mx == r) & mask
    h[idx] = (60 * ((g[idx] - b[idx]) / diff[idx])) % 360
    idx = (mx == g) & mask
    h[idx] = (60 * ((b[idx] - r[idx]) / diff[idx]) + 120) % 360
    idx = (mx == b) & mask
    h[idx] = (60 * ((r[idx] - g[idx]) / diff[idx]) + 240) % 360
    s = np.where(mx > 1e-6, diff / np.maximum(mx, 1e-6), 0.0)
    return np.column_stack([h, s, mx])


def _adjacent_to(mask: np.ndarray, faces: np.ndarray, points: np.ndarray) -> np.ndarray:
    """回傳「與 mask 內的面共用一條邊」的面。

    先焊接重複頂點 —— GLB 的 chunk 之間頂點不共用，不焊就找不到跨 chunk 的鄰接。
    """
    from collections import defaultdict

    key = np.round(points * 1000).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    welded = inv[faces]

    seed_edges: set[tuple[int, int]] = set()
    for fi in np.where(mask)[0]:
        t = welded[fi]
        for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            seed_edges.add((min(e), max(e)))

    out = np.zeros(len(faces), dtype=bool)
    if not seed_edges:
        return out
    for fi in range(len(faces)):
        if mask[fi]:
            continue
        t = welded[fi]
        for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if (min(e), max(e)) in seed_edges:
                out[fi] = True
                break
    return out


def _despeckle(labels: np.ndarray, faces: np.ndarray, points: np.ndarray,
               area: np.ndarray, min_area: float) -> tuple[np.ndarray, dict[str, int]]:
    """把太小的非混凝土色塊退回 concrete。

    以「共用邊」定義鄰接，先焊接重複頂點 —— GLB 的 15 個 chunk 之間頂點不共用，
    不焊的話同一扇門會被切成好幾塊、全被當成雜點清掉。
    """
    from collections import defaultdict

    key = np.round(points * 1000).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    welded = inv[faces]

    concrete = LABEL_IDX["itu_concrete"]
    removed: dict[str, int] = {}
    out = labels.copy()

    for name, li in LABEL_IDX.items():
        if li == concrete:
            continue
        sel = np.where(labels == li)[0]
        if not len(sel):
            continue
        edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
        for fi in sel:
            t = welded[fi]
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                edge_faces[(min(e), max(e))].append(int(fi))
        adj: dict[int, list[int]] = defaultdict(list)
        for group in edge_faces.values():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    adj[group[i]].append(group[j])
                    adj[group[j]].append(group[i])

        seen: set[int] = set()
        dropped = 0
        for f in sel:
            f = int(f)
            if f in seen:
                continue
            comp = []
            stack = [f]
            seen.add(f)
            while stack:
                u = stack.pop()
                comp.append(u)
                for w in adj[u]:
                    if w not in seen:
                        seen.add(w)
                        stack.append(w)
            if area[comp].sum() < min_area:
                out[comp] = concrete
                dropped += len(comp)
        removed[name] = dropped
    return out, removed


def _load_image(gltf: dict, binary: bytes, img_idx: int) -> np.ndarray | None:
    from io import BytesIO

    from PIL import Image

    img = gltf.get("images", [])[img_idx]
    if "bufferView" not in img:
        return None
    data, _ = _view_bytes(gltf, binary, img["bufferView"])
    with Image.open(BytesIO(data)) as im:
        return np.asarray(im.convert("RGB"))


def classify(blob: bytes, mode: str = "conservative") -> dict[str, Any]:
    """對 GLB 逐三角形分類，回傳 labels/points/tris/統計。

    mode:
      conservative（預設）— 只判 concrete 與 wood，其餘棄權後回退成 concrete
      legacy_color       — v2 行為，額外用色彩判 glass/metal（實測誤判，僅供比對）
    """
    if mode not in ("conservative", "legacy_color"):
        raise ValueError(f"未知的 mode: {mode}")
    gltf, binary = parse_glb(blob)
    meshes = gltf.get("meshes", [])

    # 先把所有 primitive 的幾何與取樣 UV 收起來，之後按「貼圖」分批取樣，
    # 一張 4096² RGB 解開就是 50 MB，一次只能開一張
    parts: list[dict[str, Any]] = []
    for mesh_idx, world in iter_mesh_instances(gltf):
        for prim_idx, prim in enumerate(meshes[mesh_idx].get("primitives", [])):
            if prim.get("mode", 4) != 4:
                continue
            attrs = prim.get("attributes", {})
            if "POSITION" not in attrs or "indices" not in prim:
                continue
            pts = read_accessor(gltf, binary, attrs["POSITION"]).astype(np.float64)
            pts = (np.hstack([pts, np.ones((len(pts), 1))]) @ world)[:, :3]
            tris = read_accessor(gltf, binary, prim["indices"]).astype(np.int64).ravel()
            tris = tris[: (len(tris) // 3) * 3].reshape(-1, 3)
            if not len(tris):
                continue
            uv = None
            if "TEXCOORD_0" in attrs:
                uv = _normalize_uv(read_accessor(gltf, binary, attrs["TEXCOORD_0"]))
            img_idx, _rgb = _material_image(gltf, prim.get("material"))
            parts.append({"pts": pts, "tris": tris, "uv": uv, "image": img_idx})

    if not parts:
        raise GlbError("GLB 內沒有可分類的三角網格")

    # 合併成單一索引空間
    all_pts: list[np.ndarray] = []
    all_tris: list[np.ndarray] = []
    off = 0
    for p in parts:
        all_pts.append(p["pts"])
        all_tris.append(p["tris"] + off)
        p["face_slice"] = (sum(len(t) for t in all_tris[:-1]), sum(len(t) for t in all_tris))
        off += len(p["pts"])
    points = np.vstack(all_pts)
    faces = np.vstack(all_tris)
    n_faces = len(faces)

    # ── 幾何特徵 ──
    v0, v1, v2 = points[faces[:, 0]], points[faces[:, 1]], points[faces[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    area = np.linalg.norm(normals, axis=1) / 2.0
    unit = normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    tilt_deg = np.degrees(np.arcsin(np.clip(np.abs(unit[:, 1]), 0, 1)))
    centroid_y = (v0[:, 1] + v1[:, 1] + v2[:, 1]) / 3.0

    is_horizontal = tilt_deg > HORIZONTAL_DEG
    is_vertical = tilt_deg < VERTICAL_DEG

    # 地板高度不能取全域最低點 —— 掃描雜訊常有比地板更低的孤立面，
    # 取到那個點會讓所有「離地高度」整體偏移（v1 就是這樣把門判在離地 1.8 m）。
    # 改用「朝上的水平面」的面積加權高度直方圖峰值，這才是真的地板。
    floor_y = estimate_floor_y(points, faces)
    height = centroid_y - floor_y

    # ── 色彩特徵（只有垂直面需要，但一次取樣全部比較單純）──
    rgb_mean = np.full((n_faces, 3), np.nan, dtype=np.float32)
    rgb_std = np.zeros(n_faces, dtype=np.float32)

    by_image: dict[int, list[dict]] = {}
    for p in parts:
        if p["uv"] is None or p["image"] is None:
            continue
        by_image.setdefault(p["image"], []).append(p)

    for img_idx, group in by_image.items():
        img = _load_image(gltf, binary, img_idx)
        if img is None:
            continue
        for p in group:
            lo, hi = p["face_slice"]
            uv = p["uv"]
            t = p["tris"]
            # 取三個頂點 + 形心共 4 點：單一像素容易踩到 atlas 的黑色邊界
            samples = []
            for k in range(3):
                samples.append(_sample_texture(img, uv[t[:, k]]))
            centroid_uv = (uv[t[:, 0]] + uv[t[:, 1]] + uv[t[:, 2]]) / 3.0
            samples.append(_sample_texture(img, centroid_uv))
            stack = np.stack(samples)                    # (4, n, 3)
            rgb_mean[lo:hi] = stack.mean(axis=0)
            rgb_std[lo:hi] = stack.std(axis=0).mean(axis=1)
        del img

    valid_color = ~np.isnan(rgb_mean[:, 0])
    hsv = np.zeros((n_faces, 3), dtype=np.float32)
    hsv[valid_color] = _rgb_to_hsv(rgb_mean[valid_color])
    hue, sat, val = hsv[:, 0], hsv[:, 1], hsv[:, 2]

    # ── 規則 ──
    labels = np.full(n_faces, LABEL_IDX["itu_concrete"], dtype=np.uint8)
    candidate = is_vertical & valid_color   # 只有垂直面才進色彩規則

    # 唯一有正面證據的類別：不透明 + 漫反射 + 色相集中的木頭
    wood = candidate & (hue >= WOOD_HUE[0]) & (hue <= WOOD_HUE[1]) \
        & (sat >= WOOD_SAT_MIN) & (val >= WOOD_VAL[0]) & (val <= WOOD_VAL[1])
    labels[wood] = LABEL_IDX["itu_wood"]

    glass = np.zeros(n_faces, dtype=bool)
    metal = np.zeros(n_faces, dtype=bool)
    if mode == "legacy_color":
        glass = candidate & ~wood & (val >= GLASS_VAL_MIN) & (sat <= GLASS_SAT_MAX) \
            & (height >= GLASS_HEIGHT_MIN_M)
        metal = candidate & ~wood & ~glass & (sat <= METAL_SAT_MAX) \
            & (val >= METAL_VAL[0]) & (val <= METAL_VAL[1]) & (rgb_std >= METAL_STD_MIN)
        labels[glass] = LABEL_IDX["itu_glass"]
        labels[metal] = LABEL_IDX["itu_metal"]

    raw_counts = {n: int((labels == i).sum()) for n, i in LABEL_IDX.items()}
    labels, despeckled = _despeckle(labels, faces, points, area, MIN_PATCH_AREA_M2)

    # ── 證據涵蓋率：哪些面是「判出來的」，哪些只是回退 ──
    # 水平面與斜面的 concrete 是幾何證據（室內不會有朝上的木門/玻璃），算有證據；
    # 垂直面的 concrete 是「色彩規則沒判出東西」的回退，沒有正面證據。
    proven = (labels == LABEL_IDX["itu_wood"]) | is_horizontal | (~is_vertical)
    if mode == "legacy_color":
        proven = proven | glass | metal
    fallback = ~proven
    total_area = float(area.sum())
    evidence = {
        "mode": mode,
        "proven_area_pct": round(100.0 * float(area[proven].sum()) / total_area, 2),
        "fallback_area_pct": round(100.0 * float(area[fallback].sum()) / total_area, 2),
        "fallback_material": "itu_concrete",
        "fallback_rationale": (
            "未判出材質的垂直面回退成不透明的混凝土：做覆蓋/隔離度時，"
            "把牆誤判成玻璃（訊號穿過去）遠比把玻璃誤判成牆嚴重"
        ),
    }

    # ── 診斷：木頭門檻到底有沒有把兩群分開 ──
    # 指標定義見 skill：算「判成 concrete、但距 wood 門檻只差一點」的面積佔比。
    # > 5% 代表兩群沒分開，門檻只是把邊界樣本搬來搬去，結果不可信。
    vert_concrete = is_vertical & (labels == LABEL_IDX["itu_concrete"])
    near_wood = vert_concrete & (hue >= WOOD_HUE[0]) & (hue <= WOOD_HUE[1]) \
        & (sat >= WOOD_SAT_MIN - 0.08) & (sat < WOOD_SAT_MIN)

    # 邊界面要再分兩種，否則指標會誤報（2026-09-08 實測 5.46% 觸發警報，
    # 逐一看圖後發現多半是門邊的混合像素，不是漏判的木頭）：
    #   - 貼著 wood 的  → 三角形跨在門與牆的交界上，顏色本來就是混合的。
    #                     這是真實物件邊界的必然產物，無害。
    #   - 沒貼著 wood 的 → 場景裡有一整片「像木頭但沒被判成木頭」的表面，
    #                     這才是門檻沒分開兩群的訊號。
    touching_wood = _adjacent_to(labels == LABEL_IDX["itu_wood"], faces, points)
    isolated_near = near_wood & ~touching_wood
    vc_area = float(area[vert_concrete].sum())
    near_pct = round(100.0 * float(area[near_wood].sum()) / vc_area, 2) if vc_area else 0.0
    iso_pct = round(100.0 * float(area[isolated_near].sum()) / vc_area, 2) if vc_area else 0.0
    diagnostics = {
        "wood_boundary_density_pct": near_pct,
        "wood_boundary_isolated_pct": iso_pct,
        "wood_boundary_reliable": bool(iso_pct <= 2.0),
        "note": (
            "near = 判成 concrete 但距 wood 門檻只差一點的面積佔比；"
            "isolated = 其中沒有貼著任何 wood 面的部分（真正的疑慮訊號，> 2% 視為門檻沒分開兩群）"
        ),
    }

    stats = {}
    total_area = float(area.sum())
    for name, i in LABEL_IDX.items():
        sel = labels == i
        stats[name] = {
            "faces": int(sel.sum()),
            "area_m2": round(float(area[sel].sum()), 2),
            "area_pct": round(100.0 * float(area[sel].sum()) / total_area, 2),
        }

    return {
        "points": points,
        "faces": faces,
        "labels": labels,
        "area": area,
        "stats": stats,
        "despeckle": {"faces_reverted_to_concrete": despeckled, "raw_face_counts": raw_counts},
        "evidence": evidence,
        "diagnostics": diagnostics,
        "geometry": {
            "total_area_m2": round(total_area, 2),
            "face_count": n_faces,
            "horizontal_pct": round(100.0 * float(area[is_horizontal].sum()) / total_area, 2),
            "vertical_pct": round(100.0 * float(area[is_vertical].sum()) / total_area, 2),
            "textured_pct": round(100.0 * float(area[valid_color].sum()) / total_area, 2),
            "floor_y": round(floor_y, 3),
            "model_y_range": [round(float(points[:, 1].min()), 3), round(float(points[:, 1].max()), 3)],
        },
    }


def _thresholds() -> dict[str, Any]:
    return {
        "min_patch_area_m2": MIN_PATCH_AREA_M2,
        "horizontal_deg": HORIZONTAL_DEG,
        "vertical_deg": VERTICAL_DEG,
        "wood_hue": WOOD_HUE,
        "wood_sat_min": WOOD_SAT_MIN,
        "wood_val": WOOD_VAL,
        "glass_val_min": GLASS_VAL_MIN,
        "glass_sat_max": GLASS_SAT_MAX,
        "glass_height_min_m": GLASS_HEIGHT_MIN_M,
        "metal_sat_max": METAL_SAT_MAX,
        "metal_val": METAL_VAL,
        "metal_std_min": METAL_STD_MIN,
    }


def classify_and_record(blob: bytes, base_path: str | Path,
                        mode: str = "conservative") -> dict[str, Any]:
    """分類並落地：{base}.materials.npz（逐面標籤）+ {base}.materials.json（統計）。

    npz 給後續產 Mitsuba 場景用；json 是人看的，同時記下當次門檻與規則版本，
    之後結果不對時能直接對照是哪一版分的。
    """
    base = Path(base_path)
    result = classify(blob, mode=mode)

    npz_path = base.with_suffix(".materials.npz")
    np.savez_compressed(
        npz_path,
        labels=result["labels"],
        label_names=np.array(LABELS),
        faces=result["faces"].astype(np.int32),
        points=result["points"].astype(np.float32),
        ruleset_version=RULESET_VERSION,
    )

    summary = {
        "ruleset_version": RULESET_VERSION,
        "thresholds": _thresholds(),
        "geometry": result["geometry"],
        "materials": result["stats"],
        "evidence": result["evidence"],
        "diagnostics": result["diagnostics"],
        "despeckle": result["despeckle"],
        "npz": npz_path.name,
    }
    json_path = base.with_suffix(".materials.json")
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    summary["npz_path"] = str(npz_path)
    summary["json_path"] = str(json_path)
    return summary


def write_preview_usd(base_path: str | Path, out_path: str | Path | None = None) -> str:
    """把分類結果輸出成一份依材質上色的 USD，方便在 Kit 裡目視檢查。"""
    from pxr import Gf, Usd, UsdGeom

    base = Path(base_path)
    data = np.load(base.with_suffix(".materials.npz"), allow_pickle=False)
    labels = data["labels"]
    faces = data["faces"].astype(np.int64)
    points = data["points"].astype(np.float64)

    out = Path(out_path) if out_path else base.with_name(base.stem + "_materials.usd")
    if out.exists():
        out.unlink()
    stage = Usd.Stage.CreateNew(str(out))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Xform.Define(stage, "/World/Materials")

    for i, name in enumerate(LABELS):
        sel = labels == i
        if not sel.any():
            continue
        tris = faces[sel]
        used, remap = np.unique(tris, return_inverse=True)
        pts = points[used]
        m = UsdGeom.Mesh.Define(stage, f"/World/Materials/{name}")
        m.CreatePointsAttr([Gf.Vec3f(*map(float, p)) for p in pts])
        m.CreateFaceVertexCountsAttr([3] * len(tris))
        m.CreateFaceVertexIndicesAttr([int(v) for v in remap.reshape(-1)])
        m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        m.CreateDoubleSidedAttr(True)
        m.CreateExtentAttr([Gf.Vec3f(*map(float, pts.min(axis=0))),
                            Gf.Vec3f(*map(float, pts.max(axis=0)))])
        m.CreateDisplayColorAttr([Gf.Vec3f(*PREVIEW_COLOR[name])])

    stage.GetRootLayer().Save()
    return str(out)
