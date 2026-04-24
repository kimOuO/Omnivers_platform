# Omniver Platform

RAN Digital Twin 控制平台。4 個 process：Postgres + Django + Next.js（3 個 docker）+ Omniverse Kit（host 上跑）。

訊號（RSRP/SINR）不在本平台計算 — 由外部「模擬 RAN (Sionna DU)」透過 `POST /api/v0.1/RAN/Ingest/SignalIngestor/create` 送入。

---

## 架構

```
┌──── host (GPU + VNC) ────┐        ┌──── Docker ────────────┐
│                          │        │                        │
│  Kit Render Server       │◄──HTTP─┤  Django backend :8001  │
│  :8080 (scene_config,    │        │    ▲                   │
│         /World/*)        │        │    │                   │
│                          │        │  Postgres :5432        │
└──────────────────────────┘        │    ▲                   │
                                    │    │                   │
                                    │  Next.js :3001 ◄─browser
                                    └────────────────────────┘
```

- Kit 固定跑 host（需要 GPU/VNC/Vulkan）
- Docker 三個容器：Postgres（DB）、Django（API/匯流排）、Next.js（Dashboard）
- Backend container 透過 `host.docker.internal:8080` 連 Kit

---

## 快速啟動（推薦：Docker）

```bash
cd /home/mitlab/Omniverse/Omniverse/Omniver_platform

# 1. 3 個容器一次起
docker compose up -d

# 2. Kit 在 host 跑（需要 DISPLAY 已設定 / VNC Session 已開）
cd kit && source ~/omniverse-env/bin/activate && ./run.sh &
cd ..

# 3. 瀏覽器打開
open http://localhost:3001
```

首次 `docker compose up` 會 build backend image（~3-5 分鐘裝 pip 依賴），之後秒開。

**在 Kit 視窗裡按 `Build Scene` → `▶ Start Animation`**，VNC 看到 5 個 UE 走動即 OK。

### 關閉
```bash
docker compose down                 # 停容器，保留 DB 資料
docker compose down -v              # 連 DB volume 一起砍
# Kit: Ctrl+C 那個 terminal
```

---

## 替代方案：本機 4-terminal 啟動（不用 Docker）

只在沒裝 Docker 或想 host 端 debug 時用。

| # | 服務 | 目錄 | 指令 | Port |
|---|---|---|---|---|
| 1 | Postgres | `Omniver-RAN/` | `docker compose up -d postgres` | 5432 |
| 2 | Kit | `kit/` | `source ~/omniverse-env/bin/activate && ./run.sh` | 8080 |
| 3 | Django | `Omniver-RAN/` | `source .venv/bin/activate && python manage.py runserver 0.0.0.0:8001` | 8001 |
| 4 | Next.js | `frontend/` | `npm run dev` | 3000/3001 |

首次需 `./shell/init_project.sh` + `./shell/run_migrations.sh`（在 `Omniver-RAN/`）和 `npm install`（在 `frontend/`）。

---

## 目錄

```
Omniver_platform/
├── docker-compose.yml            ★ 一鍵起全 stack
├── kit/                          Omniverse Kit 啟動（.kit + run.sh）
├── extensions/                   Kit Python extensions
│   ├── mitlab.ran.scene.builder/ 造景 + 動畫
│   ├── mitlab.ran.api/           Port 8080 HTTP proxy 到 USD stage
│   └── mitlab.ran.labels/        UE 頭上浮 RSRP/SINR 文字
├── Omniver-RAN/                  Django backend (依 backend_rule.md)
│   ├── main/apps/ran/            models / serializers / actors / services
│   ├── Dockerfile                (prod)
│   └── docker-compose.yml        (dev postgres-only)
├── frontend/                     Next.js (App Router, 依 frontend_rule.md)
│   ├── app/  components/  hooks/  services/  types/  config/
│   └── Dockerfile                (prod)
├── data/pg/                      Postgres volume (.gitignored)
├── docs/
│   ├── ingest_api.md             外部送訊號進平台的 API contract
│   ├── s4_smoke_test.sh          6 項 curl 驗證腳本
│   └── sequence_diagrams/        5 個 use case 的 PlantUML 時序圖
├── backend_rule.md               ★ Django 架構鐵則
├── frontend_rule.md              ★ Next.js 架構鐵則
└── README.md                     (本檔)
```

子目錄各自有 README：`kit/`、`extensions/`、`Omniver-RAN/`、`frontend/`、`docs/sequence_diagrams/`。

---

## 驗證

```bash
# 1. Postgres
docker exec omniver_postgres pg_isready -U ran -d ran_dt

# 2. Django (經 docker 映射)
curl -s -X POST http://localhost:8001/api/v0.1/RAN/Scene/SceneStateReader/read \
  -H "Content-Type: application/json" -d '{}' | python3 -m json.tool
# 成功回 {"success":true, "data":{buildings:6, gnbs:3, ues:5, animating:true}}

# 3. Frontend
curl -I http://localhost:3001    # HTTP/1.1 200 OK

# 4. Kit (host)
curl -s http://localhost:8080/scene/status

# 5. 完整 6 項煙霧測試
bash docs/s4_smoke_test.sh

# 6. 送假訊號 → VNC 裡 UE 頭上立刻出現 RSRP/SINR
curl -X POST http://localhost:8001/api/v0.1/RAN/Ingest/SignalIngestor/create \
  -H "Content-Type: application/json" \
  -d '{"ts":"2026-04-18T10:00:00Z","signals":[
        {"ue_name":"UE_Handover_Path","serving_cell":"gNB_Macro_NW",
         "rsrp_dbm":-78.2,"sinr_db":12.5,
         "rsrp_map":{"gNB_Macro_NW":-78.2,"gNB_Macro_SE":-92.1}}]}'
```

---

## 規範 & 參考

| 檔 | 用途 |
|---|---|
| `backend_rule.md` | Django 架構鐵則（POST-only URL 格式、Actor/Serializer/Service 分層、`env_loader`） |
| `frontend_rule.md` | Next.js 架構鐵則（whitelist folders、ESLint import 邊界、async state shape） |
| `docs/ingest_api.md` | 給「模擬 RAN」團隊：送訊號 / 場景初始化的 API contract |
| `docs/sequence_diagrams/` | 5 個 use case 的 PlantUML 時序圖 (UC01-05) |
| `docs/s4_smoke_test.sh` | 後端 6 項 curl 驗證腳本 |

---

## 常見問題排錯

| 症狀 | 解法 |
|---|---|
| 瀏覽器所有 API 請求 pending | Chrome extension（ad blocker 等）攔截，用**無痕視窗**或 F12→Application→Clear site data |
| Django 終端狂噴 `ConnectionRefusedError :8080` + 502 | **正常**。Kit 沒起或還沒 ready，Django 如實回 502 |
| `OSError: [Errno 28] No space left on device` | 根磁碟滿。`pip cache purge` 通常救回 5–12 GB |
| Django: `port 5432 failed` | Postgres 沒起。`docker ps` 看 `omniver_postgres` 是否 healthy |
| Kit 啟動卡在 EULA | 終端輸入 `Yes` 接受，以後不再問 |
| Kit 秒退沒視窗 | `DISPLAY` 沒設定，或用 SSH（SSH + RTX 不可行，改本機或 VNC） |
| Kit: Vulkan `Descriptor pool max count` 爆 | labels extension 設 2 Hz 更新已緩解；真的爆再 `render_only_gnb:true` |
| Docker 前端打不到後端 | 瀏覽器開 `localhost:3001`（docker map port）；F12 → Network 確認請求 URL 是 `:8001` |
| 訊號 ingest 成功但 `kit_errors > 0` | Kit 沒跑起來或 port 8080 擋住。Django 的 DB 寫入不受影響 |

---

## 現況與下一步

✅ 已完成：Kit extension + Django backend + Next.js Dashboard / Trajectory Editor + Signal Ingest + Docker compose
⏳ 未完成：
- **S7** — Signal Time Series 頁（`/signals`）：Recharts 畫 RSRP/SINR 歷史曲線
- **S8** — `PlatformReporter` 改成真實 HTTP client 上行給外部平台（目前只 log 到 DB）

---

## 授權與來源

Kit Render Server 基於 **NVIDIA Omniverse Kit SDK 110.0.0**（pip 版 `omniverse-kit`）。
本專案的 `mitlab.ran.*` extension、Django backend、Next.js frontend 為內部使用。
