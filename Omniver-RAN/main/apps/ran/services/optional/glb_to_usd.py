"""glTF/GLB → USD 轉換器（給 MapController.import_glb 用）。

為什麼不用 omni.kit.asset_converter：那支只跑得起來在 Kit 容器的事件迴圈裡，
Django 這邊呼叫不到，且轉檔要非同步等 Kit 回報。GLB 的結構單純（JSON chunk +
binary chunk），backend 已經有 usd-core 可以直接寫 USD，所以自己解析反而
最短路徑，也能完全掌握座標軸與材質怎麼落地。

座標軸：glTF 規格是 Y-up、公尺；osm_to_usd.write_usd() 建的 stage 也是
UsdGeom.Tokens.y + metersPerUnit 1.0 —— **兩邊同軸，不需要任何旋轉**。
（Omniverse 預設 Z-up 是另一回事，這個平台的 stage 一律 Y-up。）

限制（實務上掃描模型會踩到的）：
  - 不支援 Draco / KTX2 等 extensionsRequired，遇到直接報錯而非默默產出空檔
  - 只取 baseColorTexture，其餘 PBR 貼圖忽略（掃描模型通常也只有 albedo）
  - 不轉骨架/動畫/相機/燈光
"""
from __future__ import annotations

import base64
import json
import os
import struct
from pathlib import Path
from typing import Any

import numpy as np

# glTF componentType → numpy dtype
_COMPONENT_DTYPE = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}
_TYPE_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

_MIME_EXT = {"image/jpeg": ".jpg", "image/png": ".png"}

GLB_MAGIC = 0x46546C67  # 'glTF'
_CHUNK_JSON = 0x4E4F534A
_CHUNK_BIN = 0x004E4942


class GlbError(ValueError):
    """GLB 內容不合法或用到不支援的功能。"""


# ────────────────────────── 解析 ──────────────────────────

def parse_glb(blob: bytes) -> tuple[dict[str, Any], bytes]:
    """拆出 (glTF JSON, binary chunk)。長度欄位不一致就直接擋下 —— 半截的
    上傳檔若放行，會在後面 accessor 取值時變成難懂的 index error。"""
    if len(blob) < 12:
        raise GlbError("檔案太小，不是有效的 GLB")
    magic, version, length = struct.unpack("<III", blob[:12])
    if magic != GLB_MAGIC:
        raise GlbError("不是 GLB 檔（magic 不符，若為 .gltf 純文字格式請先轉成 .glb）")
    if version != 2:
        raise GlbError(f"只支援 glTF 2.0，收到 version={version}")
    if length != len(blob):
        raise GlbError(f"檔案不完整：header 宣告 {length} bytes，實際 {len(blob)} bytes")

    gltf: dict[str, Any] | None = None
    binary = b""
    off = 12
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        data = blob[off + 8:off + 8 + clen]
        if len(data) < clen:
            raise GlbError("檔案不完整：chunk 長度超出檔案結尾")
        if ctype == _CHUNK_JSON:
            gltf = json.loads(data)
        elif ctype == _CHUNK_BIN:
            binary = data
        off += 8 + clen + (-clen % 4)

    if gltf is None:
        raise GlbError("GLB 缺少 JSON chunk")

    required = gltf.get("extensionsRequired") or []
    if required:
        raise GlbError(
            "不支援的 glTF 擴充：" + ", ".join(required)
            + "（例如 Draco 壓縮 / KTX2 貼圖，請先用 gltf-transform 解壓後再匯入）"
        )
    return gltf, binary


def _buffer_bytes(gltf: dict, binary: bytes, idx: int) -> bytes:
    """取第 idx 個 buffer 的位元組。GLB 的 buffer 0 無 uri（= binary chunk）；
    其餘只支援 data: URI，外部檔案沒有一起上傳所以拿不到。"""
    buf = gltf["buffers"][idx]
    uri = buf.get("uri")
    if uri is None:
        return binary
    if uri.startswith("data:"):
        return base64.b64decode(uri.split(",", 1)[1])
    raise GlbError(f"不支援外部 buffer 檔案：{uri}")


def _view_bytes(gltf: dict, binary: bytes, view_idx: int) -> tuple[bytes, int]:
    """回傳 (該 bufferView 的位元組, byteStride)。"""
    bv = gltf["bufferViews"][view_idx]
    raw = _buffer_bytes(gltf, binary, bv.get("buffer", 0))
    off = bv.get("byteOffset", 0)
    return raw[off:off + bv["byteLength"]], bv.get("byteStride", 0)


def read_accessor(gltf: dict, binary: bytes, idx: int) -> np.ndarray:
    """讀 accessor → shape (count, n) 的 numpy 陣列，已處理 byteStride 交錯排列。"""
    acc = gltf["accessors"][idx]
    n = _TYPE_COUNT[acc["type"]]
    dtype = np.dtype(_COMPONENT_DTYPE[acc["componentType"]])
    count = acc["count"]

    if "bufferView" not in acc:  # 稀疏/全零 accessor
        return np.zeros((count, n), dtype=dtype)

    data, stride = _view_bytes(gltf, binary, acc["bufferView"])
    start = acc.get("byteOffset", 0)
    elem = dtype.itemsize * n

    if stride and stride != elem:
        # 交錯排列：逐元素跨 stride 取，不能一口氣 frombuffer
        out = np.empty((count, n), dtype=dtype)
        for i in range(count):
            o = start + i * stride
            out[i] = np.frombuffer(data, dtype=dtype, count=n, offset=o)
        return out
    return np.frombuffer(data, dtype=dtype, count=count * n, offset=start).reshape(count, n)


def _normalize_uv(uv: np.ndarray) -> np.ndarray:
    """UV 若以整數型別儲存則依 glTF 規範還原到 0..1。"""
    if uv.dtype == np.uint8:
        return uv.astype(np.float32) / 255.0
    if uv.dtype == np.uint16:
        return uv.astype(np.float32) / 65535.0
    return uv.astype(np.float32)


# ────────────────────────── node 階層 ──────────────────────────

def _node_matrix(node: dict) -> np.ndarray:
    """單一 node 的區域變換矩陣（4x4，row-vector 慣例：p' = p @ M）。"""
    if "matrix" in node:
        # glTF 的 matrix 是 column-major，轉置後即可用 row-vector 相乘
        return np.array(node["matrix"], dtype=np.float64).reshape(4, 4, order="F").T

    m = np.eye(4)
    if "scale" in node:
        m = np.diag([*node["scale"], 1.0]) @ m
    if "rotation" in node:
        x, y, z, w = node["rotation"]
        r = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0],
            [2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0],
            [2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0],
            [0, 0, 0, 1],
        ], dtype=np.float64)
        m = m @ r
    if "translation" in node:
        t = np.eye(4)
        t[3, :3] = node["translation"]
        m = m @ t
    return m


def iter_mesh_instances(gltf: dict):
    """走訪 scene 的 node 樹，yield (mesh_index, 世界變換矩陣)。

    掃描類 GLB 常見的做法是「一個 root 掛 N 個沒有 transform 的子 node」，
    但手工場景會有巢狀 transform，所以照規範完整累乘。"""
    nodes = gltf.get("nodes", [])
    scenes = gltf.get("scenes", [])
    scene_idx = gltf.get("scene", 0)
    roots = scenes[scene_idx].get("nodes", []) if scenes else list(range(len(nodes)))

    stack = [(i, np.eye(4)) for i in reversed(roots)]
    seen: set[int] = set()
    while stack:
        idx, parent = stack.pop()
        if idx in seen:  # 防禦性：規範上 node 樹不該有環
            continue
        seen.add(idx)
        node = nodes[idx]
        world = _node_matrix(node) @ parent
        if "mesh" in node:
            yield node["mesh"], world
        for child in reversed(node.get("children", [])):
            stack.append((child, world))


# ────────────────────────── 貼圖 ──────────────────────────

def _extract_images(gltf: dict, binary: bytes, tex_dir: Path) -> list[str | None]:
    """把內嵌貼圖寫成 tex_dir 底下的獨立檔，回傳每個 image 的檔名（失敗為 None）。"""
    images = gltf.get("images", [])
    if not images:
        return []
    tex_dir.mkdir(parents=True, exist_ok=True)
    out: list[str | None] = []
    for i, img in enumerate(images):
        ext = _MIME_EXT.get(img.get("mimeType", ""), ".bin")
        try:
            if "bufferView" in img:
                data, _ = _view_bytes(gltf, binary, img["bufferView"])
            elif str(img.get("uri", "")).startswith("data:"):
                head, b64 = img["uri"].split(",", 1)
                data = base64.b64decode(b64)
                if "png" in head:
                    ext = ".png"
                elif "jpeg" in head or "jpg" in head:
                    ext = ".jpg"
            else:
                out.append(None)  # 外部貼圖檔沒隨 GLB 上傳，只能跳過
                continue
        except Exception:  # noqa: BLE001
            out.append(None)
            continue
        fname = f"tex_{i:03d}{ext}"
        (tex_dir / fname).write_bytes(data)
        out.append(fname)
    return out


def _material_image(gltf: dict, mat_idx: int | None) -> tuple[int | None, list[float]]:
    """material → (baseColorTexture 對應的 image index, baseColorFactor RGB)。"""
    fallback = [0.65, 0.65, 0.65]
    if mat_idx is None:
        return None, fallback
    mat = gltf.get("materials", [])[mat_idx]
    pbr = mat.get("pbrMetallicRoughness", {}) or {}
    factor = pbr.get("baseColorFactor")
    rgb = [float(c) for c in factor[:3]] if factor else fallback
    tex_ref = pbr.get("baseColorTexture")
    if not tex_ref:
        return None, rgb
    tex = gltf.get("textures", [])[tex_ref["index"]]
    return tex.get("source"), rgb


def _index_offsets(collected: list[dict[str, Any]]) -> list[int]:
    """各 part 在合併後點陣列中的起始索引。"""
    offsets = []
    total = 0
    for c in collected:
        offsets.append(total)
        total += len(c["points"])
    return offsets


def estimate_floor_y(points: np.ndarray, faces: np.ndarray) -> float:
    """估「真正的地板高度」——不能取模型最低點。

    掃描常會帶到樓梯下方、樓下結構或飄浮雜訊，最低點比可走的地板低一大截
    （這份走廊實測差 2.15 m）。用最低點對齊地面，會讓整條走廊懸空，
    站在 y=0 的 UE 就跑到地板底下。

    改用「朝上的水平面」面積加權高度直方圖峰值：地板是室內面積最大的朝上平面。
    """
    v0, v1, v2 = points[faces[:, 0]], points[faces[:, 1]], points[faces[:, 2]]
    n = np.cross(v1 - v0, v2 - v0)
    area = np.linalg.norm(n, axis=1) / 2.0
    unit = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    up = (np.degrees(np.arcsin(np.clip(np.abs(unit[:, 1]), 0, 1))) > 60.0) & (unit[:, 1] > 0)
    if not up.any():
        return float(points[:, 1].min())
    cy = (v0[:, 1] + v1[:, 1] + v2[:, 1]) / 3.0
    ys, ws = cy[up], area[up]
    bins = np.arange(ys.min(), ys.max() + 0.1, 0.1)
    if len(bins) < 2:
        return float(ys.min())
    hist, edges = np.histogram(ys, bins=bins, weights=ws)
    i = int(hist.argmax())
    return float((edges[i] + edges[i + 1]) / 2.0)


# ────────────────────────── 主流程 ──────────────────────────

def convert_glb_to_usd(
    blob: bytes,
    out_path: str | Path,
    *,
    prim_name: str = "Mesh",
    scale: float = 1.0,
    recenter: bool = True,
    ground_align: bool = True,
    ceiling_cut_m: float | None = 2.2,
) -> dict[str, Any]:
    """GLB bytes → USD 檔，回傳統計資訊。

    recenter / ground_align：掃描模型的原點常落在拍攝起點而非場景中心，
    直接匯入會整個歪到場景邊緣。預設把水平中心移到 (0, 0)、底部貼齊 y=0，
    與 OSM 地圖「原點在場景中央、地面在 y=0」的慣例一致。

    ceiling_cut_m：把這個高度以上的面另外收進 `<root>/Ceiling` prim。
    室內掃描從外面看就是一個封閉盒子，看不到裡面有什麼；把上半部拆成獨立 prim，
    在 Kit 的 stage tree 直接把它設 invisible 就等於做了一刀水平剖面，
    可以從上往下看走廊內部與人所在位置。設 None 則不拆。
    """
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

    gltf, binary = parse_glb(blob)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tex_dirname = f"{out_path.stem}_textures"
    image_files = _extract_images(gltf, binary, out_path.parent / tex_dirname)

    # 先收集所有 primitive 的世界座標點，才能算整體 bbox 做置中
    collected: list[dict[str, Any]] = []
    meshes = gltf.get("meshes", [])
    for mesh_idx, world in iter_mesh_instances(gltf):
        mesh = meshes[mesh_idx]
        for prim_idx, prim in enumerate(mesh.get("primitives", [])):
            if prim.get("mode", 4) != 4:  # 只處理 TRIANGLES
                continue
            attrs = prim.get("attributes", {})
            if "POSITION" not in attrs:
                continue
            pts = read_accessor(gltf, binary, attrs["POSITION"]).astype(np.float64)
            homo = np.hstack([pts, np.ones((len(pts), 1))]) @ world
            pts = homo[:, :3] * scale

            if "indices" in prim:
                idx = read_accessor(gltf, binary, prim["indices"]).astype(np.int64).ravel()
            else:
                idx = np.arange(len(pts), dtype=np.int64)
            tris = idx[: (len(idx) // 3) * 3].reshape(-1, 3)
            if not len(tris):
                continue

            uv = None
            if "TEXCOORD_0" in attrs:
                raw_uv = _normalize_uv(read_accessor(gltf, binary, attrs["TEXCOORD_0"]))
                # glTF 的 UV 原點在左上、USD 在左下 → v 要翻轉，否則貼圖上下顛倒
                uv = np.column_stack([raw_uv[:, 0], 1.0 - raw_uv[:, 1]])

            img_idx, rgb = _material_image(gltf, prim.get("material"))
            collected.append({
                "name": f"mesh_{mesh_idx:03d}_{prim_idx}",
                "points": pts, "tris": tris, "uv": uv,
                "image": image_files[img_idx] if (img_idx is not None and img_idx < len(image_files)) else None,
                "rgb": rgb,
            })

    if not collected:
        raise GlbError("GLB 內沒有可轉換的三角網格（可能只含點/線或空 scene）")

    all_pts = np.vstack([c["points"] for c in collected])
    lo = all_pts.min(axis=0)
    hi = all_pts.max(axis=0)
    offset = np.zeros(3)
    if recenter:
        offset[0] = -(lo[0] + hi[0]) / 2.0
        offset[2] = -(lo[2] + hi[2]) / 2.0
    all_faces = np.vstack([c["tris"] + s for c, s in zip(collected, _index_offsets(collected))])
    floor_y = estimate_floor_y(all_pts, all_faces)
    if ground_align:
        # 對齊「估到的地板」而不是最低點 —— 這樣 y=0 就是人站的那個面
        offset[1] = -floor_y
    if offset.any():
        for c in collected:
            c["points"] = c["points"] + offset

    # ── 寫 USD（Y-up / 公尺，與 osm_to_usd 的 stage 慣例一致）──
    if out_path.exists():
        out_path.unlink()
    stage = Usd.Stage.CreateNew(str(out_path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world_prim = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world_prim.GetPrim())
    root = f"/World/{prim_name}"
    UsdGeom.Xform.Define(stage, root)
    UsdGeom.Scope.Define(stage, f"{root}/Looks")

    # 同一張貼圖只建一個 material，避免 15 個 prim 各自複製一份 shader 網路
    mat_cache: dict[tuple[str | None, tuple[float, float, float]], Any] = {}

    def get_material(image: str | None, rgb: list[float]):
        key = (image, tuple(round(c, 4) for c in rgb))
        if key in mat_cache:
            return mat_cache[key]
        mid = len(mat_cache)
        mpath = f"{root}/Looks/mat_{mid:03d}"
        mat = UsdShade.Material.Define(stage, mpath)
        surf = UsdShade.Shader.Define(stage, f"{mpath}/Surface")
        surf.CreateIdAttr("UsdPreviewSurface")
        surf.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.85)
        surf.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
        if image:
            reader = UsdShade.Shader.Define(stage, f"{mpath}/stReader")
            reader.CreateIdAttr("UsdPrimvarReader_float2")
            reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
            tex = UsdShade.Shader.Define(stage, f"{mpath}/diffuseTex")
            tex.CreateIdAttr("UsdUVTexture")
            # 相對路徑：USD 與貼圖資料夾一起搬動時才不會斷連結
            tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(f"./{tex_dirname}/{image}")
            tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
                reader.ConnectableAPI(), "result"
            )
            tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
            tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
            tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
            surf.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
                tex.ConnectableAPI(), "rgb"
            )
        else:
            surf.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
        mat.CreateSurfaceOutput().ConnectToSource(surf.ConnectableAPI(), "surface")
        mat_cache[key] = mat
        return mat

    if ceiling_cut_m is not None:
        UsdGeom.Xform.Define(stage, f"{root}/Interior")
        UsdGeom.Xform.Define(stage, f"{root}/Ceiling")

    def _prim_path(name: str, upper: bool) -> str:
        if ceiling_cut_m is None:
            return f"{root}/{name}"
        return f"{root}/{'Ceiling' if upper else 'Interior'}/{name}"

    tri_total = 0
    ceiling_faces = 0
    for c in collected:
        groups: list[tuple[np.ndarray, bool]] = [(c["tris"], False)]
        if ceiling_cut_m is not None:
            # 以三角形形心高度分組。用形心而非頂點，避免跨越切面的三角形被重複計入
            cy = c["points"][c["tris"]][:, :, 1].mean(axis=1)
            upper_mask = cy > float(ceiling_cut_m)
            groups = [(c["tris"][~upper_mask], False), (c["tris"][upper_mask], True)]
            ceiling_faces += int(upper_mask.sum())

        for tris, upper in groups:
            if not len(tris):
                continue
            # 只帶這一組用到的頂點，Ceiling 才不會扛著整份 points
            used, remap = np.unique(tris, return_inverse=True)
            sub_pts = c["points"][used]
            sub_tris = remap.reshape(-1, 3)
            m = UsdGeom.Mesh.Define(stage, _prim_path(c["name"], upper))
            m.CreatePointsAttr([Gf.Vec3f(*map(float, p)) for p in sub_pts])
            m.CreateFaceVertexCountsAttr([3] * len(sub_tris))
            m.CreateFaceVertexIndicesAttr([int(v) for v in sub_tris.ravel()])
            m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
            # 室內掃描的面法線幾乎全部朝向房間內側，從外部視角看到的是背面。
            # RTX 預設剔除背面 → 整個模型在 viewport 上「消失」（2026-09-07 實際踩到）。
            m.CreateDoubleSidedAttr(True)
            # 沒有 extent，Hydra 的視錐剔除與 Frame Selection 都會誤判
            m.CreateExtentAttr([Gf.Vec3f(*map(float, sub_pts.min(axis=0))),
                                Gf.Vec3f(*map(float, sub_pts.max(axis=0)))])
            if c["uv"] is not None:
                st = UsdGeom.PrimvarsAPI(m.GetPrim()).CreatePrimvar(
                    "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex
                )
                st.Set([Gf.Vec2f(float(u), float(v)) for u, v in c["uv"][used]])
            else:
                m.CreateDisplayColorAttr([Gf.Vec3f(*c["rgb"])])
            # 先 Apply schema 再 Bind — 少了 Apply，USD 讀回時會噴
            # "Found material bindings but MaterialBindingAPI is not applied" 警告
            UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(get_material(c["image"], c["rgb"]))
            tri_total += len(sub_tris)

    stage.GetRootLayer().Save()

    final_lo = lo + offset
    final_hi = hi + offset
    return {
        "mesh_count": len(collected),
        "triangle_count": int(tri_total),
        "vertex_count": int(sum(len(c["points"]) for c in collected)),
        "material_count": len(mat_cache),
        "texture_count": sum(1 for f in image_files if f),
        "extent_ew_m": float(final_hi[0] - final_lo[0]),
        "extent_ns_m": float(final_hi[2] - final_lo[2]),
        "height_max_m": float(final_hi[1]),
        "usd_path": str(out_path),
        "texture_dir": tex_dirname if any(image_files) else "",
        "ceiling_cut_m": ceiling_cut_m,
        "floor_y_offset_m": round(float(floor_y - lo[1]), 3),  # 真地板高於模型最低點多少
        "ceiling_faces": ceiling_faces,
        "size_bytes": os.path.getsize(out_path),
    }
