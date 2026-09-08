# 計劃：Dashboard 2D 畫布升級 3D ＋ 2026_9_6.glb 整合

> **進度（2026-09-08）**：Part A（A1–A4）✅、B1 ✅、B1b ✅、B2 未動。
> 途中修正的兩個計劃錯誤：
> 1. **不需要 Y-up → Z-up 旋轉**。`osm_to_usd.write_usd()` 的 stage 是
>    `UsdGeom.Tokens.y` + metersPerUnit 1.0，與 glTF 同軸。
> 2. 前端不是 `Omnivers_platform/frontend`，而是
>    **`/home/mitlab/XAPP_DT/Physics_sim/Dashboard`**（Next 15 / React 19），
>    畫布是 `components/TopDownMap.tsx` 的 SVG 俯視圖。
>
> 另外實測發現：匯入的 USD 一定要寫 **`doubleSided=true`** 與 **`extent`**，
> 否則室內掃描的面法線朝內會被 RTX 背面剔除，在 Kit viewport 上完全看不到。

## 0. 現況盤點（已實測）

**前端**：`/home/mitlab/XAPP_DT/Physics_sim/Dashboard`（Next 15.5.15 / React 19.2.5）
- 畫布元件 = `components/TopDownMap.tsx`（615 行，**SVG 俯視 2D**，非 canvas/WebGL）
- 座標系：`SCENE_MIN=-500` ~ `SCENE_MAX=500`（公尺），x→螢幕 x、z→螢幕 y（翻轉），**y 高度被丟棄**
- 兩處使用：`app/editor/page.tsx:832`、`app/playback/page.tsx:75`
- 已具備的互動：拖曳 building / gnb / cell / ue / waypoint、點選物件、coverage heatmap 疊圖、A→B 路徑規劃
- 資料已含 3D 資訊但目前沒畫出來：`Building.position:[x,y,z]`、`size:[x,y,z]`、`color`、`rotation_xyz_deg`、`usd_path`；`mapFootprints[].height`（`footprintColor()` 已用高度上色來「模擬」3D 感）

**GLB**：`2026_9_6.glb`（27.9 MB）
- 合法 glTF 2.0；15 mesh / 90,726 tri / 15 張 4K JPEG baseColor
- 室內走廊實景掃描，約 14 × 6.3 × 65.6 m（Y-up），表面積 1,281 m²
- 無 NORMAL、無 name、無材質語意、無地理座標；**開放邊 16.5%（24,468 / 148,323）不封閉**

---

## Part A：前端 2D → 3D（建議先做，價值最高、風險最低）

### 技術選型：react-three-fiber
| 方案 | 評價 |
|---|---|
| **@react-three/fiber + drei**（建議） | React 19 相容（fiber v9 / drei v10）；宣告式，現有 props 介面幾乎原封不動；拖曳靠 raycast 換算，改動集中 |
| 原生 three.js | 要自己管 imperative 生命週期，跟 React state 同步易出 bug |
| Kit WebRTC 串流 | 畫質最好但吃 GPU、延遲高，且**失去前端側的點選/拖曳編輯能力**——不適合取代編輯器 |
| deck.gl | 強在地理大資料，這裡是 ±500 m 局部場景，殺雞用牛刀 |

```bash
cd /home/mitlab/XAPP_DT/Physics_sim/Dashboard
npm i three @react-three/fiber @react-three/drei
npm i -D @types/three
```

### 步驟

**A1. 新增 `components/Scene3D.tsx`，與 TopDownMap 並存**
- **不要直接改寫 TopDownMap**。維持完全相同的 Props 介面，editor 頁加一個 `2D / 3D` 切換鈕，2D 隨時可退回。這是這步能低風險的關鍵。

**A2. 場景骨架**
- `<Canvas camera={{ position:[300,300,300], fov:50 }}>` + `<OrbitControls>` + `<Grid>`（1000×1000 對齊 ±500）
- 燈光：`ambientLight` + `directionalLight`（掃描模型無法線，需靠打光）
- **座標約定**：three.js 與 glTF 同為 Y-up，跟後端 `[x,y,z]` 直接對應，**不需轉換**；只有匯入 Omniverse USD（Z-up）時才要轉。

**A3. 物件渲染**
- Building：`<mesh position={position}><boxGeometry args={size}/>` + `rotation_xyz_deg` 轉弧度
- mapFootprints：`THREE.Shape` + `ExtrudeGeometry`，沿用現有 `footprintColor(h)` 配色
- gNB：圓柱 + 扇形波束示意；UE：小球 + `<Line>` 畫軌跡
- Coverage heatmap：貼在 y≈0.1 的 `PlaneGeometry` + `DataTexture`（把現有 `valToColor()` 寫進 texture，不要用幾千個 mesh）

**A4. 互動移植（最花時間的一步）**
- 點選：R3F 內建 `onPointerDown`，直接取代 SVG 的 hit test
- **拖曳**：SVG 版是 2D 像素反推座標；3D 要改成 **ray 與 y=0 平面求交**（`THREE.Plane` + `raycaster.ray.intersectPlane`），拿到 (x, z) 後回呼**沿用現有 `onMoveBuilding/onMoveGnb/onMoveUE`**，後端與 state 邏輯零改動

**A5. 效能**
- 同型物件多時用 `<Instances>`；heatmap 用單張 texture；`<Canvas frameloop="demand">` 靜止時不重繪

**估算**：A1–A3 約半天可看到畫面；A4 互動對齊是主要工時。

---

## Part B：GLB 匯入（B1 可做，B2 需先評估）

### B1. 進 Omniverse Kit ✅
`kit/ran_server.kit` 已含 `omni.kit.asset_converter-5.1.2`、`omni.kit.tool.asset_importer-5.1.4`。
- 轉檔：GLB → USD，輸出到 `assets/maps/`（該目錄在 `docker-compose.yml` 有 **backend/Kit 同路徑 bind mount**，兩邊解析到同一檔）
- **必做**：Y-up → Z-up，套 **-90° 繞 X 軸**旋轉，否則走廊會躺著
- 現況 repo 全域 grep `glb|gltf` **零命中**，沒有自動化路徑，需新增一支轉檔 script（可仿 `services/optional/osm_to_usd.py` 的輸出慣例）

### B1b. 進前端 3D ✅（Part A 完成後幾乎免費）
`useGLTF('/models/2026_9_6.glb')` 一行就能載。但 27.9 MB 對瀏覽器偏重，上線前建議：
- `gltf-transform optimize` 做 Draco 幾何壓縮 + KTX2 貼圖壓縮，一般可壓到 5–8 MB
- 貼圖 4K×15 張是體積主因，可降到 2K

### B2. 進 Sionna ❌ 現狀不可行
Sionna 走的是 `osm_to_usd.py:366 write_mitsuba()` 的 **Mitsuba XML + 每材質一個 PLY**，靠 BSDF id 判定 radio material：
```python
MATERIAL_MAP = {"concrete":"itu_concrete", "glass":"itu_glass",
                "metal":"itu_metal", "brick":"itu_brick", "wood":"itu_wood"}
```
GLB 缺的正是這個。三個必須先解決的硬傷：
1. **開放邊 16.5%** → 射線從破洞漏出，路徑損耗失真。需補洞封閉化（MeshLab / Open3D Poisson）
2. **無材質語意** → 15 個 material 只有照片貼圖，全部會 fallback 成 `itu_concrete`，木門/玻璃/混凝土被當同一種
3. **無地理座標** → 無法與 gNB/UE 世界座標對齊，需定位錨點

工作量不小，**建議 Part A + B1 完成、確認視覺正確後再單獨評估**。

---

## 建議順序
1. **Part A**（前端 3D）— 獨立、可驗證、對現有功能零破壞
2. **B1**（GLB → USD → Kit）— 小工，驗證模型正確性
3. **B1b**（GLB 壓縮後進前端 3D）— A 完成後幾乎免費
4. **B2**（Sionna）— 前三步結果出來再決定是否投入
