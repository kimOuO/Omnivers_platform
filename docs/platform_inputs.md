# Omniver Platform 輸入規格

**給**：要第一次啟動整套 Omniver Digital Twin 平台、或把它移到新機器上的人
**版本**：v0.1
**更新日期**：2026-04-22

這份文件列完整份平台跑起來需要的所有「輸入」，包含：**硬體條件 / 外部資產 / 場景定義 / 環境變數 / runtime 資料流**。
不是教學，是 checklist 式規格。

---

## 0. 架構速覽

```
┌──────────────────────────────────────────────────────────────────┐
│  Host (Linux + NVIDIA GPU)                                       │
│                                                                  │
│   Omniverse Kit (:8080 HTTP, :8081 WS)                          │
│     └─ scene.builder + api + labels extensions                   │
│         讀 ← /home/mitlab/Omniverse/Omniverse/scene_config.json  │
│                                                                  │
│   Docker network "omniver_default"                               │
│   ├─ omniver_postgres   :5432                                    │
│   ├─ omniver_backend    :8001  (Django + Channels)              │
│   └─ omniver_frontend   :3001  (Next.js)                         │
│                                                                  │
│   Docker network "dt-ueinference_default"                        │
│   ├─ dt_postgres        :5433                                    │
│   └─ dt-ueinference     :8002                                    │
│                                                                  │
│   Docker network "ranp-sim_default"                              │
│   └─ ranp-sim           :8000                                    │
└──────────────────────────────────────────────────────────────────┘
```

3 個 compose stack 是獨立的；透過 `host.docker.internal` 互相串。

---

## 1. 硬體 / 系統前置

| 項目 | 必需 | 備註 |
|---|---|---|
| NVIDIA GPU | ✅ | Kit 要 RTX 40 系或以上；驗過 RTX 4060 Laptop / RTX A4000 |
| NVIDIA driver | ✅ | 版本 ≥ 535 |
| Docker Engine | ✅ | ≥ 24.0 |
| Docker Compose | ✅ | v2（`docker compose` 命令）|
| `host.docker.internal` 解析 | ✅ | Linux 需在 compose 加 `extra_hosts: - host.docker.internal:host-gateway`（已在 compose 內）|
| 可用 ports | ✅ | 3001 / 5432 / 5433 / 8000 / 8001 / 8002 / 8080 / 8081 都不能被佔 |
| Disk | ✅ | Kit install ≥ 30 GB；DB volume 10 GB；USD 資產集 ≥ 5 GB |
| NVIDIA Omniverse Kit SDK | ✅ | 跟 `kit-app-template` 配套的 SDK 版本 |
| VNC / 本機顯示 | ✅ | Kit viewport 需要 X server；遠端用 TurboVNC |

---

## 2. 必要的外部檔案（host 路徑）

| 絕對路徑 | 用途 | 誰用 |
|---|---|---|
| `/home/mitlab/Omniverse/Omniverse/scene_config.json` | 場景 source-of-truth | Kit scene.builder、dt-ueinference、ranp-sim |
| `/home/mitlab/omniverse/USD_dataset/Characters_NVD@10012/...` | UE 角色 USD | Kit scene.builder 載入 UE |
| `/home/mitlab/omniverse/USD_dataset/AECDemo_NVD@10012/...` | 建築 USD（可選）| Kit scene.builder 載入建築 |
| `/home/mitlab/Omniverse/Omniverse/ranp-sim/scenes/umi_3sector.xml` | Mitsuba 場景（ray-tracing）| ranp-sim |

**若這些路徑不在**：Kit 場景建不出來（會用 fallback cube 取代），但其他服務可啟動。
**ranp-sim 的 Mitsuba XML 缺**：ranp-sim 算 coverage / signal 會失敗。

---

## 3. `scene_config.json` 格式規範

**這是整個平台的場景 source-of-truth**。Kit 直接讀它建 3D；dt-ueinference 也會讀它做 ingest payload；ranp-sim 啟動時掛 read-only 看 gNB / 建築。

### 3.1 頂層欄位

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `render_only_gnb` | bool | ❌ | 只渲 gNB（debug 用） |
| `skip_buildings` | bool | ❌ | 略過建築 |
| `skip_ues` | bool | ❌ | 略過 UE |
| `gnb_visual_scale` | float | ❌ | gNB 視覺大小倍率 |
| `environment.template_usd` | string \| null | ❌ | 環境模板 USD（天空/地面）|
| `ue_asset.usd` | string | ❌ | 預設 UE 的 USD 絕對路徑 |
| `ue_asset.target_height_m` | float | ❌ | UE 高度縮放目標（米）|
| `ground` | object | ✅ | `{ size: [x,z], position: [x,y,z] }` |
| `buildings` | array | ✅ | 建築清單（見 3.2）|
| `gnbs` | array | ✅ | gNB 清單（見 3.3）|
| `ues` | array | ✅ | UE 清單（見 3.4）|

### 3.2 `buildings[]`

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `name` | string | ✅ | 唯一識別，USD prim path `/World/{name}` |
| `position` | `[x,y,z]` | ✅ | 公尺，Y-up |
| `size` | `[x,y,z]` | ✅ | 公尺，Y 是高度 |
| `color` | `[r,g,b]` 0–1 | ❌ | fallback cube 時顏色 |
| `material` | string | ❌ | 材質名 (`concrete` 等) |
| `usd` | string | ❌ | 絕對路徑的 USD，覆寫 cube |
| `target_height_m` | float | ❌ | USD 縮放到這高度 |
| `rotation_xyz_deg` | `[rx,ry,rz]` | ❌ | 歐拉角（度）|

### 3.3 `gnbs[]`

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `name` | string | ✅ | 唯一，前綴必須 `gNB_` |
| `pci` | int | ✅ | Physical Cell ID（0–1007）|
| `cell_id` | string | ✅ | 3GPP cell identifier（hex）|
| `position` | `[x,y,z]` | ✅ | gNB 天線中心，Y 是地面高度 |
| `scale` | float | ❌ | 視覺縮放 |
| `frequency_ghz` | float | ✅ | 載波頻率 |
| `power_dbm` | float | ✅ | 發射功率 |
| `bandwidth_mhz` | float | ✅ | 頻寬 |
| `color` | `[r,g,b]` 0–1 | ❌ | 視覺色 |

### 3.4 `ues[]`

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `name` | string | ✅ | 唯一，前綴必須 `UE_` |
| `position` | `[x,y,z]` | ✅ | 初始位置 |
| `color` | `[r,g,b]` 0–1 | ❌ | fallback 視覺色 |
| `target_height_m` | float | ❌ | USD 角色縮放高度 |
| `usd` | string | ❌ | 替代預設 UE USD |
| `waypoints` | `[[x,y,z],...]` | ❌ | 至少 2 點；無則 UE 靜止 |
| `speed_mps` | float | ❌ | 移動速度；未填 1.0 |

### 3.5 座標系約定

```
+X = 東（East）    → 前端 map 向右
-X = 西（West）    → 前端 map 向左
+Z = 北（North）   → 前端 map 向上
-Z = 南（South）   → 前端 map 向下
+Y = 上（Up）      → 高度
```

**單位永遠是公尺**。整個場域在 250 × 250 m 範圍內。

---

## 4. 服務環境變數

每個 service 自己有 `.env.sample`，複製成 `.env` 後套變數。

### 4.1 Omniver-RAN backend（`Omniver_platform/Omniver-RAN/.env`）

| Key | 預設 | 說明 |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev-change-me | production 必換 |
| `DJANGO_DEBUG` | True | production 設 False |
| `DJANGO_ALLOWED_HOSTS` | localhost,127.0.0.1 | 加上部署域名 |
| `DJANGO_SETTINGS_MODULE` | `main.settings.local` | |
| `DB_HOST` | postgres | docker service 名 |
| `DB_PORT` | 5432 | |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | ran_dt / ran / ran | |
| `HTTP_KIT_HOST` | host.docker.internal | 連 host 上的 Kit |
| `HTTP_KIT_PORT` | 8080 | Kit HTTP 服務 port |
| `WS_KIT_PORT` | 8081 | Kit WS push port |
| `LOG_LEVEL` | INFO | |

### 4.2 dt-ueinference（`dt-ueinference/.env`）

| Key | 預設 | 說明 |
|---|---|---|
| `HTTP_PORT` | 8002 | |
| `DB_*` | dt_postgres / dt / dt | 獨立 DB，不共用 Omniver |
| `OMNIVER_BASE_URL` | http://host.docker.internal:8001 | 呼叫 Omniver API |
| `OMNIVER_WS_URL` | ws://host.docker.internal:8001/api/v0.1/RAN/UE/live | 訂 UE live |
| `RANPSIM_BASE_URL` | http://host.docker.internal:8000 | 呼叫 ranp-sim |
| `SCENE_CONFIG_PATH` | /mnt/srcin/scene_config.json | read-only bind mount |
| `SCENE_ID` | umi_3sector_v1 | 必須對得上 ranp-sim 載入的 scene id |
| `TICK_INTERVAL_MS` | 500 | tick loop 週期 |
| `E2_SNAPSHOT_KEEP_MAX` | 500 | E2 保留筆數上限 |

### 4.3 ranp-sim（`ranp-sim/.env`）

| Key | 預設 | 說明 |
|---|---|---|
| `HTTP_PORT` | 8000 | |
| `SCENE_CONFIG_PATH` | /mnt/srcin/scene_config.json | read-only |
| `MITSUBA_SCENE_PATH` | /app/scenes/umi_3sector.xml | ray-tracing 用 |
| `SCENE_ID` | umi_3sector_v1 | |
| `SIM_DEFAULT_FREQ_GHZ` | 3.5 | |
| `SIM_MAX_DEPTH` | 5 | bounce 數 |
| `SIM_MAX_UES_PER_TICK` | 50 | |
| `SIM_NOISE_FIGURE_DB` | 7 | |

### 4.4 Frontend（`frontend/.env.local`）

| Key | 預設 | 說明 |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | http://localhost:8001 | 指向 Omniver backend |
| `NEXT_PUBLIC_WS_URL` | ws://localhost:8001/api/v0.1/RAN/UE/live | 同上 WS |

---

## 5. Runtime 輸入（startup 後還要灌的東西）

### 5.1 初始化（一次性）

| Step | 指令 / API |
|---|---|
| DB schema | `docker compose exec backend python manage.py migrate` |
| 建 3D 場景 | 在 Kit UI 點 **Build Scene** 或 `POST /api/v0.1/RAN/Scene/SceneController/build` |
| 開始動畫 | 在 Kit UI 點 **Start** 或 `POST /api/v0.1/RAN/Scene/AnimationController/start` |
| 註冊場景到 DB | `POST /api/v0.1/RAN/Ingest/SceneIngestor/create`（body = scene_config 內容）|

### 5.2 持續輸入（誰負責）

| 資料 | 誰負責推 | 頻率 | 端點 |
|---|---|---|---|
| UE 訊號（RSRP / SINR）| RAN 模擬器（ranp-sim 或 OAI gNB + Sionna）| 1–10 Hz | `POST /api/v0.1/RAN/Ingest/SignalIngestor/create` |
| UE 位置更新 | Kit 自己（動畫寫 translate）| 60 Hz 內部，2 Hz 出 WS | 不用外部推 |
| UE 軌跡變更 | 前端 Trajectory Editor | 使用者按 Apply 時 | `POST /api/v0.1/RAN/UE/UEController/trajectory` |
| gNB 參數變更 | 前端 gNB table | 使用者改值時 | `POST /api/v0.1/RAN/GNB/GNBController/update` |

---

## 6. 最少可跑的起步組合

### 6.1 「只看 3D 場景」
- Host: Kit + `scene_config.json` + USD assets
- 不用 Docker
- 能跑：viewport / labels / 動畫 / UE 移動

### 6.2 「3D + 前端 dashboard」
- 6.1 + `docker compose up -d`（3 個 omniver service）
- 能跑：前端看場景 / 改 gNB / 改軌跡 / 看歷史
- **缺**：UE 訊號是假的（沒有 RAN 模擬器推進來）

### 6.3 「完整平台」
- 6.2 + ranp-sim `docker compose up -d` + dt-ueinference `docker compose up -d`
- 能跑：RSRP/SINR 由 Sionna 真算 / coverage heatmap / E2 報告 / 完整 tick loop

---

## 7. 啟動順序（依賴從下往上）

```
1. Postgres（omniver_postgres + dt_postgres）
2. Django backend（等 postgres healthy）
3. Kit on host（任何時候都能啟，但 build scene 需要 scene_config.json 存在）
4. ranp-sim（獨立，不依賴其他）
5. dt-ueinference（需要 Omniver + ranp-sim 活著才有意義）
6. Frontend（依賴 backend）
```

Kit 要**最後才 Build Scene**，否則 SceneIngestor 推進來時 Kit 還沒準備好接 build 指令。

---

## 8. 驗收 checklist

- [ ] `curl localhost:8080/scene/status` 回 JSON（Kit 活）
- [ ] `curl -X POST localhost:8001/api/v0.1/RAN/Scene/SceneStateReader/read -d '{}' -H 'Content-Type: application/json'` 回 200（Django → Kit 通）
- [ ] 瀏覽器開 `http://localhost:3001` 看到 dashboard（前端活）
- [ ] 按 F12 → Network → WS connection `/api/v0.1/RAN/UE/live` `101 Switching Protocols`（WS 通）
- [ ] `curl -X POST localhost:8002/api/v0.1/DTUEInference/UE/HealthChecker/read -d '{}' -H 'Content-Type: application/json'` 回 200（bridge 活）
- [ ] `curl -X POST localhost:8000/api/v0.1/RanpSim/RanSignal/HealthChecker/read -d '{}' -H 'Content-Type: application/json'` 回 200（sim 活）

6 項全綠 = 整套平台起飛。

---

## 9. 常見坑

| 症狀 | 根因 | 修法 |
|---|---|---|
| `port is already allocated 5432` | 舊 `omniver_ran_postgres` container 還在 | `docker rm omniver_ran_postgres` |
| 前端 404 一大片 | backend 還在冷啟動 URLConf 沒載完 | 等 5-10s 再刷新 |
| Kit viewport 全黑 / 缺 UE 角色 | USD 資產路徑對不到 | 檢查 `/home/mitlab/omniverse/USD_dataset/` 存在 |
| SceneIngestor 推了但 Kit 沒畫 | 兩條路徑解耦（故意的）| 要另外呼叫 `SceneController/build` |
| ranp-sim 回 404 scene | `SCENE_ID` 對不上 | 三個 service 的 `SCENE_ID` 要一致 |
| WS 一直 reconnect | Kit :8081 沒開 或 Kit 掛 | 檢查 Kit 是否 running |
| gNB 改了前端沒更新 | frontend SceneLayout 只取 1 次 | 刷新頁面；或改 hook 加 refetch |

---

## 10. 相關文件

- API 完整清單：`docs/api.md`
- Ingest 規格：`docs/ingest_api.md`
- Kit 內部說明：`docs/kit_internals_101.md`
- ranp-sim 輸入規格：`ranp-sim/docs/INPUT_SPEC.md`
- dt-ueinference：`dt-ueinference/README.md`
- 後端鐵則：`backend_rule.md`
