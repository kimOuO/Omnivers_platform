"""合成「掃描風格」的 GLB 測試場景，附逐面 ground truth 材質。

為什麼需要這個：材質分類的門檻全部是在**一份**走廊掃描上調出來的，
換場景會不會崩只能推論。真實的第二份掃描還沒有，但可以合成——
只要合成的東西保留掃描的關鍵特徵（三角化、頂點雜訊、破洞、貼圖來自照片
而非純色），就能測出「規則有沒有編碼到不該編碼的東西」。

能測什麼 / 不能測什麼（很重要）：
  ✅ 幾何規則是否過度貼合走廊尺度（籃球場 9 m 天花板、小辦公室 2.3 m 天花板）
  ✅ 材質假設是否隱含「木頭一定是門」（體育館的木地板）
  ✅ 色彩門檻在不同光線/白平衡下的穩定度
  ❌ photogrammetry 真實的重建缺陷（貼圖接縫、幾何漂移、深度誤差）
  ❌ 真實材質的外觀多樣性（合成貼圖是程序生成的，不是照片）

所以這是**必要條件測試**：合成場景過不了的，真實場景一定過不了；
合成場景過得了的，真實場景仍需驗證。
"""
from __future__ import annotations

import json
import struct
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

# ground truth 材質
GT_MATERIALS = ["concrete", "wood", "glass", "metal"]

# 各材質的程序貼圖參數：(基底 RGB, 雜訊強度, 是否加高光)
_TEX_SPEC = {
    "concrete": ((196, 194, 188), 18, False),
    "wood": ((132, 74, 32), 22, False),
    "glass": ((236, 240, 244), 10, True),
    "metal": ((178, 180, 184), 8, True),
}


def _make_texture(kind: str, size: int = 128, rng=None) -> bytes:
    """程序生成材質貼圖。刻意不用純色 —— 分類器會取多點平均，純色會讓
    飽和度分布退化成 delta function，測不出真實的邊界行為。"""
    rng = rng or np.random.default_rng(0)
    base, noise, spec = _TEX_SPEC[kind]
    img = np.zeros((size, size, 3), dtype=np.float32)
    img[:] = base
    img += rng.normal(0, noise, img.shape)
    if kind == "wood":                      # 木紋：沿一軸的低頻條紋
        grain = np.sin(np.linspace(0, 18 * np.pi, size))[:, None] * 14
        img += grain[:, :, None]
    if spec:                                # 鏡面/透明表面：加一塊高光
        yy, xx = np.mgrid[0:size, 0:size]
        hot = np.exp(-(((xx - size * 0.35) ** 2 + (yy - size * 0.4) ** 2) / (2 * (size * 0.22) ** 2)))
        img += hot[:, :, None] * 55
    buf = BytesIO()
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(buf, format="JPEG", quality=92)
    return buf.getvalue()


class SceneBuilder:
    """累積三角形 + 逐面 ground truth，最後輸出 GLB。"""

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)
        self.tris: list[np.ndarray] = []
        self.gt: list[str] = []

    def quad(self, p0, p1, p2, p3, material: str) -> None:
        """一個四邊形 → 兩個三角形。頂點順序決定法線方向。"""
        for tri in ((p0, p1, p2), (p0, p2, p3)):
            self.tris.append(np.array(tri, dtype=np.float64))
            self.gt.append(material)

    def subdivided_quad(self, p0, p1, p2, p3, material: str, cell_m: float = 0.35) -> None:
        """細分成掃描尺度的小三角形（真實掃描平均邊長約 17 cm）。

        不細分的話一面牆只有 2 個三角形，區域成長、連通分量、破洞偵測
        全部退化，測不到真實行為。
        """
        p0, p1, p2, p3 = (np.asarray(p, dtype=np.float64) for p in (p0, p1, p2, p3))
        nu = max(1, int(np.linalg.norm(p1 - p0) / cell_m))
        nv = max(1, int(np.linalg.norm(p3 - p0) / cell_m))
        for i in range(nu):
            for j in range(nv):
                u0, u1 = i / nu, (i + 1) / nu
                v0, v1 = j / nv, (j + 1) / nv

                def at(u, v):
                    return (p0 * (1 - u) * (1 - v) + p1 * u * (1 - v)
                            + p2 * u * v + p3 * (1 - u) * v)

                self.quad(at(u0, v0), at(u1, v0), at(u1, v1), at(u0, v1), material)

    def box(self, centre, size, material: str, cell_m: float = 0.35) -> None:
        """一個長方體（家具、設備、柱子）。"""
        cx, cy, cz = centre
        sx, sy, sz = (s / 2 for s in size)
        c = [(cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz),
             (cx + sx, cy - sy, cz + sz), (cx - sx, cy - sy, cz + sz),
             (cx - sx, cy + sy, cz - sz), (cx + sx, cy + sy, cz - sz),
             (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz)]
        for a, b, d, e in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
                           (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            self.subdivided_quad(c[a], c[b], c[d], c[e], material, cell_m)

    # ── 掃描擬真 ──
    def add_scan_noise(self, jitter_m: float = 0.012, dropout: float = 0.01) -> None:
        """加頂點抖動與隨機破面，模擬掃描重建的不完美。

        沒有這一步，合成場景的平面完美到區域成長一次就吃掉整面牆，
        測不出真實資料上「牆被切碎」的行為。
        """
        # 抖動必須以「唯一頂點」為單位。對 (n,3,3) 的三角形陣列直接加，會讓
        # 同一個頂點在不同三角形裡被抖到不同位置，焊接完全失效，每個面自成
        # 一個 segment（實測 6 萬個面 → 6 萬個 segment，合併迴圈直接爆炸）。
        # 真實 photogrammetry 的頂點在 chunk 內是共用的。
        tris = np.array(self.tris)
        flat = tris.reshape(-1, 3)
        key = np.round(flat * 1000).astype(np.int64)
        uniq, inv = np.unique(key, axis=0, return_inverse=True)
        tris = (flat + self.rng.normal(0, jitter_m, (len(uniq), 3))[inv]).reshape(tris.shape)
        keep = self.rng.random(len(tris)) > dropout
        self.tris = list(tris[keep])
        self.gt = [g for g, k in zip(self.gt, keep) if k]

    def photometric(self, exposure: float = 1.0, wb=(1.0, 1.0, 1.0)) -> tuple[float, tuple]:
        return exposure, wb

    def write_glb(self, path: str | Path, exposure: float = 1.0,
                  wb: tuple[float, float, float] = (1.0, 1.0, 1.0)) -> dict:
        """輸出 GLB。每個 ground truth 材質一張貼圖，逐面指派 UV。"""
        tris = np.array(self.tris, dtype=np.float32)
        gt = np.array(self.gt)
        used = [m for m in GT_MATERIALS if (gt == m).any()]

        # 幾何：逐面獨立頂點（與 photogrammetry 輸出一致，頂點不共用）
        positions = tris.reshape(-1, 3)
        # UV：每個三角形鋪滿整張貼圖的一角，帶點隨機偏移避免退化
        uvs = np.tile(np.array([[0.08, 0.08], [0.92, 0.12], [0.5, 0.9]], dtype=np.float32),
                      (len(tris), 1))
        uvs += self.rng.normal(0, 0.02, uvs.shape).astype(np.float32)
        uvs = np.clip(uvs, 0.02, 0.98)

        images, image_bytes = [], []
        for m in used:
            raw = _make_texture(m, rng=self.rng)
            if exposure != 1.0 or wb != (1.0, 1.0, 1.0):
                im = np.asarray(Image.open(BytesIO(raw))).astype(np.float32)
                im = im * exposure * np.array(wb, dtype=np.float32)
                buf = BytesIO()
                Image.fromarray(np.clip(im, 0, 255).astype(np.uint8)).save(buf, "JPEG", quality=92)
                raw = buf.getvalue()
            image_bytes.append(raw)

        # 按材質分組成 primitive
        prims, idx_chunks = [], []
        for mi, m in enumerate(used):
            sel = np.where(gt == m)[0]
            idx = np.concatenate([[3 * s, 3 * s + 1, 3 * s + 2] for s in sel]).astype(np.uint32)
            idx_chunks.append((mi, idx))

        bin_parts, views, accessors = [], [], []
        offset = 0

        def add_view(data: bytes, target=None):
            nonlocal offset
            pad = (-len(data)) % 4
            bin_parts.append(data + b"\x00" * pad)
            v = {"buffer": 0, "byteOffset": offset, "byteLength": len(data)}
            if target:
                v["target"] = target
            views.append(v)
            offset += len(data) + pad
            return len(views) - 1

        pos_view = add_view(positions.astype(np.float32).tobytes(), 34962)
        uv_view = add_view(uvs.astype(np.float32).tobytes(), 34962)
        pos_acc = len(accessors)
        accessors.append({"bufferView": pos_view, "componentType": 5126, "count": len(positions),
                          "type": "VEC3",
                          "min": positions.min(axis=0).tolist(),
                          "max": positions.max(axis=0).tolist()})
        uv_acc = len(accessors)
        accessors.append({"bufferView": uv_view, "componentType": 5126, "count": len(uvs),
                          "type": "VEC2"})

        for mi, idx in idx_chunks:
            iv = add_view(idx.tobytes(), 34963)
            acc = len(accessors)
            accessors.append({"bufferView": iv, "componentType": 5125,
                              "count": len(idx), "type": "SCALAR"})
            prims.append({"attributes": {"POSITION": pos_acc, "TEXCOORD_0": uv_acc},
                          "indices": acc, "material": mi, "mode": 4})

        for raw in image_bytes:
            v = add_view(raw)
            images.append({"bufferView": v, "mimeType": "image/jpeg"})

        gltf = {
            "asset": {"version": "2.0", "generator": "scene_synth"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": prims}],
            "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": i}}}
                          for i in range(len(used))],
            "textures": [{"source": i, "sampler": 0} for i in range(len(used))],
            "samplers": [{"wrapS": 10497, "wrapT": 10497}],
            "images": images,
            "bufferViews": views,
            "accessors": accessors,
            "buffers": [{"byteLength": offset}],
        }

        bin_blob = b"".join(bin_parts)
        js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        js += b" " * ((-len(js)) % 4)
        total = 12 + 8 + len(js) + 8 + len(bin_blob)
        out = (struct.pack("<III", 0x46546C67, 2, total)
               + struct.pack("<II", len(js), 0x4E4F534A) + js
               + struct.pack("<II", len(bin_blob), 0x004E4942) + bin_blob)
        Path(path).write_bytes(out)

        # ground truth 以「primitive 分組後的面順序」落地，與分類器展開順序一致
        gt_ordered = np.concatenate([np.full(len(idx) // 3, mi) for mi, idx in idx_chunks])
        np.savez_compressed(Path(path).with_suffix(".gt.npz"),
                            material_of_face=gt_ordered,
                            material_names=np.array(used))
        return {"path": str(path), "faces": len(tris), "materials": used,
                "gt_counts": {m: int((gt == m).sum()) for m in used}}


# ────────────────────────── 場景 ──────────────────────────

def _room(b: SceneBuilder, w: float, d: float, h: float, floor_mat="concrete",
          wall_mat="concrete", ceil_mat="concrete") -> None:
    """一個朝內的房間外殼（掃描室內看到的是內表面）。"""
    x0, x1 = -w / 2, w / 2
    z0, z1 = -d / 2, d / 2
    b.subdivided_quad((x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1), floor_mat)
    b.subdivided_quad((x0, h, z1), (x1, h, z1), (x1, h, z0), (x0, h, z0), ceil_mat)
    b.subdivided_quad((x0, 0, z0), (x0, h, z0), (x0, h, z1), (x0, 0, z1), wall_mat)
    b.subdivided_quad((x1, 0, z1), (x1, h, z1), (x1, h, z0), (x1, 0, z0), wall_mat)
    b.subdivided_quad((x0, 0, z1), (x0, h, z1), (x1, h, z1), (x1, 0, z1), wall_mat)
    b.subdivided_quad((x1, 0, z0), (x1, h, z0), (x0, h, z0), (x0, 0, z0), wall_mat)


def _door(b: SceneBuilder, x: float, z: float, axis: str, width=0.9, height=2.05) -> None:
    """貼在牆面上的門板（略微內凹，與真實掃描一致）。"""
    inset = 0.04
    if axis == "x":
        b.subdivided_quad((x - inset, 0, z - width / 2), (x - inset, height, z - width / 2),
                          (x - inset, height, z + width / 2), (x - inset, 0, z + width / 2), "wood")
    else:
        b.subdivided_quad((x - width / 2, 0, z - inset), (x - width / 2, height, z - inset),
                          (x + width / 2, height, z - inset), (x + width / 2, 0, z - inset), "wood")


def _window(b: SceneBuilder, x: float, z: float, axis: str, width=1.6, sill=0.95, top=2.25) -> None:
    inset = 0.06
    if axis == "x":
        b.subdivided_quad((x - inset, sill, z - width / 2), (x - inset, top, z - width / 2),
                          (x - inset, top, z + width / 2), (x - inset, sill, z + width / 2), "glass")
    else:
        b.subdivided_quad((x - width / 2, sill, z - inset), (x - width / 2, top, z - inset),
                          (x + width / 2, top, z - inset), (x + width / 2, sill, z - inset), "glass")


def corridor(seed=0) -> SceneBuilder:
    """基準：與真實掃描同型的走廊（14 x 65 m、天花板 3.2 m）。"""
    b = SceneBuilder(seed)
    _room(b, 6.0, 40.0, 3.2)
    for z in range(-16, 17, 6):
        _door(b, -3.0, float(z), "x")
        _door(b, 3.0, float(z) + 3, "x")
    for z in range(-14, 15, 10):
        _window(b, 3.0, float(z), "x")
    b.add_scan_noise()
    return b


def classroom(seed=1) -> SceneBuilder:
    """教室：中等房間、整排窗、白板、桌椅。"""
    b = SceneBuilder(seed)
    _room(b, 9.0, 8.0, 3.0)
    _door(b, -4.5, -2.0, "x")
    for z in (-2.5, 0.0, 2.5):
        _window(b, 4.5, z, "x", width=2.0)
    b.subdivided_quad((-3, 0.9, -3.98), (-3, 2.1, -3.98), (3, 2.1, -3.98), (3, 0.9, -3.98), "metal")
    for i in range(4):
        for j in range(3):
            b.box((-2.5 + j * 2.2, 0.37, -1.5 + i * 1.2), (1.2, 0.75, 0.55), "wood", cell_m=0.25)
    b.add_scan_noise()
    return b


def laboratory(seed=2) -> SceneBuilder:
    """實驗室：金屬工作檯、玻璃櫃、設備箱。"""
    b = SceneBuilder(seed)
    _room(b, 8.0, 7.0, 2.9)
    _door(b, -4.0, 0.0, "x")
    _window(b, 4.0, 1.5, "x", width=2.4)
    for i in range(3):
        b.box((-2.0 + i * 2.0, 0.45, 0.0), (1.6, 0.9, 0.8), "metal", cell_m=0.25)
    b.subdivided_quad((-3.5, 1.0, 3.4), (-3.5, 2.4, 3.4), (0.5, 2.4, 3.4), (0.5, 1.0, 3.4), "glass")
    for i in range(2):
        b.box((2.0 + i * 1.2, 0.8, 2.8), (0.9, 1.6, 0.6), "metal", cell_m=0.25)
    b.add_scan_noise()
    return b


def gymnasium(seed=3) -> SceneBuilder:
    """籃球場：跨距大、天花板 9 m、**木地板**（測「水平面一律混凝土」的假設）。"""
    b = SceneBuilder(seed)
    _room(b, 28.0, 44.0, 9.0, floor_mat="wood")
    for z in (-12.0, 0.0, 12.0):
        _window(b, 14.0, z, "x", width=3.0, sill=5.0, top=7.5)
        _window(b, -14.0, z, "x", width=3.0, sill=5.0, top=7.5)
    _door(b, -14.0, -20.0, "x", width=1.8, height=2.4)
    for z in (-20.0, 20.0):                    # 籃板（玻璃）
        b.subdivided_quad((-0.9, 2.9, z), (-0.9, 4.0, z), (0.9, 4.0, z), (0.9, 2.9, z), "glass")
    b.add_scan_noise()
    return b


def small_office(seed=4) -> SceneBuilder:
    """小辦公室：天花板僅 2.35 m、牆面 < 8 m²（測牆面判定的兩條門檻）。"""
    b = SceneBuilder(seed)
    _room(b, 3.0, 2.6, 2.35)
    _door(b, -1.5, 0.0, "x", height=2.0)
    _window(b, 1.5, 0.0, "x", width=1.1, sill=0.9, top=1.9)
    b.box((0.0, 0.37, 0.6), (1.4, 0.75, 0.7), "wood", cell_m=0.2)
    b.add_scan_noise()
    return b


SCENES = {
    "corridor": corridor,
    "classroom": classroom,
    "laboratory": laboratory,
    "gymnasium": gymnasium,
    "small_office": small_office,
}
