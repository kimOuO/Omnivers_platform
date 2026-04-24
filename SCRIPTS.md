# 🚀 啟動和停止腳本使用指南

三個自動化腳本，詳細的步驟說明和中止方法。

---

## 📁 三個腳本概覽

| 腳本 | 用途 | 方式 | 何時使用 |
|------|------|------|---------|
| **start.sh** | 完整啟動 (6 步) | 交互式，每步確認 | 第一次啟動或完全重啟 |
| **stop.sh** | 完整停止 (4 步) | 交互式，逐步停止 | 下班或維護時 |
| **run.sh** | 菜單控制 (14 項) | 菜單選擇 | 需要靈活控制 |

---

## 🟢 start.sh - 啟動腳本

### 概述

一步步引導啟動整個 RAN Omniverse Platform。包含 6 個步驟，每步都有詳細說明和確認。

### 執行方式

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform
./start.sh
```

### 六個步驟詳解

#### 步驟 1️⃣：檢查前置條件

```
📍 檢查前置條件...
   ℹ️  發現 ~/omniverse-env，將自動激活
   ✓ Docker 已安裝
   ⚠ DISPLAY 未設定 (可選警告)
   ✓ 前置條件檢查通過

[按 Enter 繼續 或 Ctrl+C 中止]
```

**檢查項目：**
- Python venv (`~/omniverse-env/bin/activate`)
- Docker 命令
- `scene_config.json` 存在
- `DISPLAY` 環境變數（可選）
- extscache 目錄（可選警告）

**若檢查失敗：** 腳本會顯示修復方法，然後退出

---

#### 步驟 2️⃣：啟動 Docker 容器

```
📍 檢查 Docker 容器狀態...
📍 將啟動 3 個容器：
   ℹ️  1. omniver_postgres (port 5432) - 數據庫
   ℹ️  2. omniver_backend  (port 8001) - Django API
   ℹ️  3. omniver_frontend (port 3001) - Next.js 前端
   ℹ️  首次啟動會 build backend image (3-5 分鐘)

[按 Enter 繼續 或 Ctrl+C 中止]

📍 執行 docker compose up -d...
   $ cd /home/mitlab/XAPP_DT/Omnivers_platform && docker compose up -d
[+] Running 3/3
 ✓ Container omniver_postgres started
 ✓ Container omniver_backend started  
 ✓ Container omniver_frontend started

✓ Docker 容器已啟動

[按 Enter 繼續]
```

**說明：**
- 若容器已運行，會跳過啟動
- 首次執行會下載和 build 鏡像（3-5 分鐘）
- 之後秒啟

---

#### 步驟 3️⃣：啟動 Kit

```
📍 準備啟動 Kit...
   ℹ️  Kit 是 RAN Digital Twin 的 3D 核心
   ℹ️  - 需要 GPU 和顯示器（X11 或 VNC）
   ℹ️  - 首次啟動可能需要接受 EULA
   ℹ️  - 將在背景執行，持續監聽 port 8080

   ✓ venv 已激活
   ✓ DISPLAY = :0

[按 Enter 繼續]

📍 執行 ./kit/run.sh...
   $ cd /home/mitlab/XAPP_DT/Omnivers_platform/kit && ./run.sh
   （在背景執行，日誌寫入 /home/mitlab/XAPP_DT/Omnivers_platform/kit.log）

✓ Kit 已在背景啟動
   ℹ️  PID: 12345
   ℹ️  日誌位置：/home/mitlab/XAPP_DT/Omnivers_platform/kit.log
   ℹ️  查看日誌：tail -f /home/mitlab/XAPP_DT/Omnivers_platform/kit.log

[按 Enter 繼續]
```

**說明：**
- Kit 在背景執行（不會卡住終端）
- PID 保存在 `.kit.pid` 文件（用於停止時識別進程）
- 日誌實時寫入 `kit.log`
- 首次執行可能出現 EULA 提示（在 kit.log 中，輸入 Yes）

---

#### 步驟 4️⃣：等待服務初始化

```
📍 等待服務初始化...
   ℹ️  Kit 初始化需要時間（包括 Vulkan 初始化）
   ℹ️  預計：10-20 秒

   正在等待...
   ⏳ Django (port 8001).....✓
   ⏳ Next.js (port 3001)...✓
   ⏳ Postgres (port 5432).✓
   ⏳ Kit HTTP (port 8080)..................✓

[按 Enter 繼續]
```

**說明：**
- 每 1 秒嘗試一次連接
- 若超時會顯示 ⏱ 並繼續（Kit 可能正在初始化）
- 這是正常的，不會影響啟動

---

#### 步驟 5️⃣：驗證所有服務

```
📍 檢查 Postgres...
   ✓ Postgres 就緒

📍 檢查 Django...
   ✓ Django API 正常

📍 檢查 Next.js...
   ✓ Next.js 前端就緒

📍 檢查 Kit HTTP API...
   ✓ Kit HTTP API 正常

[按 Enter 繼續]
```

**說明：**
- 若有服務顯示 ⚠ 或 ✗，代表初始化中
- 若 Kit 顯示失敗，檢查 DISPLAY 和 GPU

---

#### 步驟 6️⃣：顯示完整狀態

```
════════════════════════════════════════════════════════
✓ 所有服務已啟動
════════════════════════════════════════════════════════

🌐 服務地址：
   • Next.js 前端：     http://localhost:3001
   • Django 後端：      http://localhost:8001
   • Kit HTTP API：     http://localhost:8080
   • Postgres DB：      localhost:5432
   • VNC 3D 視圖：      localhost:5901

📊 查看狀態：
   $ docker compose ps
   $ curl http://localhost:8080/scene/status
   $ tail -f /home/mitlab/XAPP_DT/Omnivers_platform/kit.log

🎮 下一步：
   1️⃣  打開 VNC 或本地 X 視窗
   2️⃣  看到 Kit 視窗後，點擊『Build Scene』
   3️⃣  打開 http://localhost:3001 控制平台

🛑 中止方法：
   • 停止一切：/home/mitlab/XAPP_DT/Omnivers_platform/stop.sh
   • 只停止 Docker：docker compose down
   • 只停止 Kit：kill $(cat .kit.pid)
   • Ctrl+C 中止此腳本（已在背景執行，無影響）

📖 更多資訊：
   $ cat /home/mitlab/XAPP_DT/Omnivers_platform/QUICKSTART.md
   $ cat /home/mitlab/XAPP_DT/Omnivers_platform/extensions/README.md

════════════════════════════════════════════════════════
祝你使用愉快！🚀
════════════════════════════════════════════════════════
```

---

### 中止 start.sh

#### 方式 1：在任何步驟按 Ctrl+C

```bash
# 正在等待時按 Ctrl+C
[按 Enter 繼續 或 Ctrl+C 中止]
^C
# ✗ 啟動被中止
```

**結果：** 腳本立即停止，已啟動的服務保留運行

#### 方式 2：在另一個終端執行 stop.sh

```bash
./stop.sh
```

**結果：** 逐步停止 Kit 和 Docker

#### 方式 3：只停止 Kit

```bash
kill $(cat .kit.pid)
```

#### 方式 4：只停止 Docker

```bash
docker compose down
```

---

## 🔴 stop.sh - 停止腳本

### 概述

一步步停止整個系統。包含 4 個步驟，清晰顯示停止過程。

### 執行方式

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform
./stop.sh
```

### 四個步驟詳解

#### 步驟 1️⃣：停止 Kit

```
════════════════════════════════════════════════════════
步驟 1️⃣  停止 Kit 程序
════════════════════════════════════════════════════════

📍 檢查 Kit 狀態...
   ℹ️  Kit 正在運行
   ℹ️  PID: 12345
   ℹ️  將發送 SIGTERM 信號...
   $ kill 12345

   ✓ Kit 已停止

[按 Enter 繼續]
```

**說明：**
- 先發送 SIGTERM（優雅停止）
- 等待 2 秒
- 若仍在執行，發送 SIGKILL（強制停止）
- 刪除 `.kit.pid` 文件

---

#### 步驟 2️⃣：停止 Docker

```
════════════════════════════════════════════════════════
步驟 2️⃣  停止 Docker 容器
════════════════════════════════════════════════════════

📍 檢查 Docker 容器狀態...
   ℹ️  發現 3 個運行中的容器：
   CONTAINER ID   IMAGE              STATUS
   xxx            omniver_postgres   Up 5 minutes
   xxx            omniver_backend    Up 5 minutes
   xxx            omniver_frontend   Up 5 minutes

   ℹ️  停止選項：
   ℹ️  1️⃣  保留數據庫（推薦）：docker compose down
   ℹ️  2️⃣  刪除數據庫數據：docker compose down -v

[按 Enter 繼續]

📍 執行 docker compose down...
   $ cd /home/mitlab/XAPP_DT/Omnivers_platform && docker compose down
[+] Running 3/3
 ✓ Container omniver_frontend stopped
 ✓ Container omniver_backend stopped
 ✓ Container omniver_postgres stopped

   ✓ Docker 容器已停止

[按 Enter 繼續]
```

**說明：**
- 默認使用 `docker compose down`（保留數據庫）
- 若要清除數據庫：`docker compose down -v`
- 容器停止不影響下次快速啟動

---

#### 步驟 3️⃣：清理和驗證

```
════════════════════════════════════════════════════════
步驟 3️⃣  清理和驗證
════════════════════════════════════════════════════════

📍 清理臨時文件...
   ✓ Kit PID 文件已刪除

📍 驗證所有服務已停止...
   Kit 程序：     ✓ 已停止
   Docker 容器：  ✓ 已停止
   HTTP :8080：  ✓ 已釋放
   HTTP :8001：  ✓ 已釋放
   HTTP :3001：  ✓ 已釋放

[按 Enter 繼續]
```

**說明：**
- 檢查 Kit 進程是否真的停止
- 檢查 Docker 容器是否停止
- 檢查所有 port 是否釋放

---

#### 步驟 4️⃣：顯示摘要

```
════════════════════════════════════════════════════════
步驟 4️⃣  停止完成
════════════════════════════════════════════════════════

✓ 所有服務已停止

📊 當前狀態：
   $ docker compose ps
   $ pgrep -f 'omni.kit_app' || echo '無運行的 Kit 程序'

🗄️  數據庫：
   ✓ Postgres 數據已保留
   若要完全清除數據：
   $ docker compose down -v

🔄 重新啟動：
   $ /home/mitlab/XAPP_DT/Omnivers_platform/start.sh

📖 查看日誌：
   $ cat /home/mitlab/XAPP_DT/Omnivers_platform/startup.log
   $ cat /home/mitlab/XAPP_DT/Omnivers_platform/kit.log

════════════════════════════════════════════════════════
系統已完全停止 👋
════════════════════════════════════════════════════════
```

---

### 中止 stop.sh

#### 方式 1：在任何步驟按 Ctrl+C

```bash
📍 檢查 Docker 容器狀態...
^C
# ✗ 停止被中止
```

**結果：** 停止過程中止，已停止的服務保留停止狀態

#### 方式 2：重新執行 stop.sh

```bash
./stop.sh
```

**結果：** 從頭開始停止

---

## 🎮 run.sh - 菜單腳本

### 概述

互動式菜單，可選擇 14 個操作。無需記住複雜命令。

### 執行方式

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform
./run.sh
```

### 菜單畫面

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🚀 RAN Omniverse Platform - 控制菜單                   ║
║                                                           ║
║   選擇操作或按 Ctrl+C 退出                              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

╔ 核心操作 ════════════════════════════════════════════════╗
║                                                           ║
║  1️⃣  啟動完整系統  (Docker + Kit + 驗證)               ║
║      一鍵啟動，所有操作自動化                            ║
║                                                           ║
║  2️⃣  停止所有服務  (Kit + Docker)                      ║
║      保留數據庫，可隨時重啟                              ║
║                                                           ║
╚════════════════════════════════════════════════════════════╝

... (其他菜單項) ...

請選擇 [1-9/0/@/d/r/h/q]:
```

---

### 菜單選項詳解

#### 1️⃣ 啟動完整系統

```bash
請選擇 [1-9/0/@/d/r/h/q]: 1

正在啟動完整系統...
(按 Ctrl+C 隨時中止)

# 執行 start.sh 的完整流程
```

#### 2️⃣ 停止所有服務

```bash
請選擇 [1-9/0/@/d/r/h/q]: 2

正在停止所有服務...
(按 Ctrl+C 隨時中止)

# 執行 stop.sh 的完整流程
```

#### 3️⃣ 只啟動 Docker

```bash
請選擇 [1-9/0/@/d/r/h/q]: 3

只啟動 Docker 容器...
[+] Running 3/3
 ✓ Container omniver_postgres started
 ✓ Container omniver_backend started
 ✓ Container omniver_frontend started

✓ Docker 容器已啟動
CONTAINER ID   IMAGE              STATUS
xxx            omniver_postgres   Up 2 minutes
xxx            omniver_backend    Up 2 minutes
xxx            omniver_frontend   Up 2 minutes

按 Enter 返回菜單...
_
```

#### 4️⃣ 只停止 Docker

```bash
請選擇 [1-9/0/@/d/r/h/q]: 4

停止 Docker 容器...
[+] Stopping 3/3
 ✓ Container omniver_frontend stopped
 ✓ Container omniver_backend stopped
 ✓ Container omniver_postgres stopped

✓ Docker 容器已停止

提示：數據庫數據已保留
若要刪除所有數據：docker compose down -v

按 Enter 返回菜單...
_
```

#### 5️⃣ 只啟動 Kit

```bash
請選擇 [1-9/0/@/d/r/h/q]: 5

啟動 Kit 程序...

✓ Kit 已在背景啟動
  PID: 12345
  日誌: /home/mitlab/XAPP_DT/Omnivers_platform/kit.log

按 Enter 返回菜單...
_
```

#### 6️⃣ 只停止 Kit

```bash
請選擇 [1-9/0/@/d/r/h/q]: 6

停止 Kit (PID: 12345)...

✓ Kit 已停止

按 Enter 返回菜單...
_
```

#### 7️⃣ 查看系統狀態

```bash
請選擇 [1-9/0/@/d/r/h/q]: 7

╔═══════════════════════════════════════════════════════════╗
║                      系統狀態                             ║
╚═══════════════════════════════════════════════════════════╝

📦 Docker 容器：
CONTAINER ID   IMAGE              STATUS
xxx            omniver_postgres   Up 2 minutes
xxx            omniver_backend    Up 2 minutes
xxx            omniver_frontend   Up 2 minutes

🎮 Kit 程序：
  ✓ Kit 正在運行 (PID: 12345)

🌐 網路服務：
  Next.js 前端 (port 3001)：✓ 就緒
  Django 後端 (port 8001)：✓ 就緒
  Kit HTTP API (port 8080)：✓ 就緒
  Postgres DB (port 5432)：✓ 就緒

按 Enter 返回菜單...
_
```

#### 8️⃣ 查看 Kit 日誌

```bash
請選擇 [1-9/0/@/d/r/h/q]: 8

╔═══════════════════════════════════════════════════════════╗
║                    Kit 日誌 (實時)                        ║
║          (按 Ctrl+C 停止跟蹤，返回菜單)                   ║
╚═══════════════════════════════════════════════════════════╝

[mitlab.ran.scene.builder] Extension startup
[mitlab.ran.api] Extension startup
[mitlab.ran.api] HTTP :8080  WS :8001
[mitlab.ran.labels] Extension startup
...
```

**說明：** 按 Ctrl+C 停止跟蹤，返回菜單

#### 9️⃣ 查看啟動日誌

```bash
請選擇 [1-9/0/@/d/r/h/q]: 9

# 顯示 startup.log 的最後 50 行
# 按空格翻頁，q 返回菜單
```

#### 🔟 驗證所有服務

```bash
請選擇 [1-9/0/@/d/r/h/q]: 0

驗證所有服務...

Postgres DB：   ✓
Django 後端：   ✓
Next.js 前端：  ✓
Kit HTTP API：  ✓

✓ 所有服務就緒！

按 Enter 返回菜單...
_
```

#### ⓪ 測試 HTTP API

```bash
請選擇 [1-9/0/@/d/r/h/q]: 0

測試 Kit HTTP API...

GET http://localhost:8080/

{
  "name": "RAN Digital Twin API",
  "version": "0.2.0",
  "endpoints": [
    "GET  /scene/status",
    "GET  /gnbs",
    "GET  /ues",
    ...
  ]
}

按 Enter 返回菜單...
_
```

#### @ 測試 Django

```bash
請選擇 [1-9/0/@/d/r/h/q]: @

測試 Django 後端...

POST http://localhost:8001/api/v0.1/RAN/Scene/SceneStateReader/read

{
  "success": true,
  "data": {
    "buildings": 6,
    "gnbs": 3,
    "ues": 5,
    "animating": false
  }
}

按 Enter 返回菜單...
_
```

#### d 查看快速開始

```bash
請選擇 [1-9/0/@/d/r/h/q]: d

# 打開 QUICKSTART.md
# 按空格翻頁，q 返回菜單
```

#### r 查看完整文檔

```bash
請選擇 [1-9/0/@/d/r/h/q]: r

# 打開 extensions/README.md
# 按空格翻頁，q 返回菜單
```

#### h 顯示幫助

```bash
請選擇 [1-9/0/@/d/r/h/q]: h

╔═══════════════════════════════════════════════════════════╗
║                      使用說明                             ║
╚═══════════════════════════════════════════════════════════╝

快速開始：
  1. 選擇 '1️⃣ 啟動完整系統' - 自動啟動所有服務
  2. 等待 10-15 秒完成初始化
  3. 打開瀏覽器：http://localhost:3001

中止方法：
  • 在任何輸入界面按 Ctrl+C 中止
  • 或選擇 '2️⃣ 停止所有服務'
  • 或選擇 '6️⃣ 只停止 Kit' + '4️⃣ 只停止 Docker'

... (更多說明) ...

按 Enter 返回菜單...
_
```

#### q 退出菜單

```bash
請選擇 [1-9/0/@/d/r/h/q]: q

再見！
```

---

### 中止 run.sh

#### 方式 1：按 Ctrl+C

```bash
# 在菜單輸入時
請選擇 [1-9/0/@/d/r/h/q]: ^C

# 或在操作執行時
正在啟動完整系統...
(按 Ctrl+C 隨時中止)
^C
```

**結果：** 菜單退出（已執行的操作保留）

#### 方式 2：選擇 q 退出

```bash
請選擇 [1-9/0/@/d/r/h/q]: q

再見！
```

**結果：** 正常退出菜單

---

## 📊 應用場景

### 場景 1：第一次啟動（推薦使用 start.sh）

```bash
./start.sh
# 一次性按 6 次 Enter，10-15 秒內完成
```

**優點：** 自動化程度最高，清晰的進度反饋

---

### 場景 2：需要靈活操作（使用 run.sh）

```bash
./run.sh
# 選擇 1 啟動，或其他選項
```

**優點：** 可選擇單獨啟動 Kit 或 Docker，查看日誌和狀態

---

### 場景 3：快速停止（使用 stop.sh）

```bash
./stop.sh
# 按幾次 Enter 完成停止
```

**優點：** 清晰的停止步驟，驗證所有服務已停止

---

### 場景 4：使用菜單完整控制（使用 run.sh）

```bash
./run.sh
# 1 - 啟動
# 7 - 查看狀態
# 8 - 查看日誌
# 0 - 驗證服務
# 2 - 停止
```

**優點：** 一個命令入口，所有操作都可做

---

## 🔍 故障排查

### Kit 無法啟動

```bash
# 查看 Kit 日誌
tail -f kit.log

# 常見原因：
# 1. DISPLAY 未設定
#    export DISPLAY=:0 (本地) 或 :88 (VNC)
#
# 2. GPU 驅動問題
#    nvidia-smi 檢查
#
# 3. 首次啟動卡在 EULA
#    在 kit.log 裡看到提示，輸入 Yes
```

---

### Docker 無法啟動

```bash
# 檢查 Docker daemon
docker ps

# 啟動 Docker
sudo systemctl start docker

# 清除所有容器
docker compose down -v
docker compose up -d
```

---

### 服務連接超時

```bash
# 這是正常的！等待更久
sleep 30
curl http://localhost:8080/

# 或用菜單檢查
./run.sh
# 選擇 7 查看系統狀態
```

---

## 📖 完整命令參考

| 目的 | 命令 |
|------|------|
| 完整啟動（詳細步驟） | `./start.sh` |
| 完整停止（詳細步驟） | `./stop.sh` |
| 菜單控制 | `./run.sh` |
| 只啟動 Docker | `./run.sh` 然後選 3 或 `docker compose up -d` |
| 只啟動 Kit | `./run.sh` 然後選 5 或 `cd kit && ./run.sh` |
| 查看 Kit 日誌 | `./run.sh` 然後選 8 或 `tail -f kit.log` |
| 驗證服務 | `./run.sh` 然後選 0 或 `curl http://localhost:8080/` |

---

## ✅ 清單

### 啟動檢單

- [ ] 執行 `./start.sh`
- [ ] 通過前置條件檢查
- [ ] Docker 容器啟動
- [ ] Kit 在背景運行
- [ ] 等待服務初始化
- [ ] 所有服務驗證通過
- [ ] 看到完整狀態摘要
- [ ] 打開 http://localhost:3001
- [ ] 在 VNC 點擊「Build Scene」

### 停止清單

- [ ] 執行 `./stop.sh`
- [ ] Kit 已停止
- [ ] Docker 容器已停止
- [ ] 清理完成
- [ ] 所有 port 已釋放
- [ ] 數據庫數據已保留（或選擇刪除）

---

## 🎯 最佳實踐

1. **首次啟動** → 使用 `./start.sh`
2. **日常操作** → 使用 `./run.sh` 菜單
3. **調試問題** → 使用菜單的「查看日誌」選項
4. **停止系統** → 使用 `./stop.sh`
5. **保留數據** → 不使用 `docker compose down -v`

---

現在你完全掌握了這三個腳本！按照需要選擇使用。🚀
