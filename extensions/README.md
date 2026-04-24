# RAN Omniverse Extensions

你的三個 Omniverse Python extensions，實現 RAN Digital Twin 的完整業務邏輯。

---

## 📦 三個 Extensions 概覽

| Extension | 職責 | 依賴 | 啟動順序 |
|-----------|------|------|---------|
| **mitlab.ran.scene.builder** | 場景建構 + 動畫管理 + USD 操作 | 無 | 1️⃣ 第一 |
| **mitlab.ran.api** | HTTP REST API + WebSocket 推送 + 命令隊列 | scene.builder + websockets | 2️⃣ 第二 |
| **mitlab.ran.labels** | UE/gNB 頭上浮標（2D HUD） | omni.ui + omni.kit.viewport | 3️⃣ 第三 |

---

## 🗂️ 目錄結構

```
extensions/
├── README.md (本檔)
│
├── mitlab.ran.scene.builder/
│   ├── config/extension.toml          ← Omniverse 看這個文件
│   ├── mitlab/ran/scene/builder/
│   │   ├── __init__.py
│   │   ├── extension.py               ← 你的代碼入點
│   │   ├── builder.py                 ← USD 操作邏輯
│   │   └── animation.py               ← 動畫管理
│   └── docs/
│
├── mitlab.ran.api/
│   ├── config/extension.toml
│   ├── mitlab/ran/api/
│   │   ├── __init__.py
│   │   ├── extension.py               ← HTTP 伺服器 + 命令隊列
│   │   └── ws_server.py               ← WebSocket 推送
│   └── docs/
│
└── mitlab.ran.labels/
    ├── config/extension.toml
    ├── mitlab/ran/labels/
    │   ├── __init__.py
    │   ├── extension.py               ← 2D 浮標渲染
    │   └── label_renderer.py
    └── docs/
```

---

## 🎯 四層架構對應

```
層 4️⃣ 設施層
  └─ extension.toml (依賴聲明)

層 3️⃣ 框架層
  ├─ on_startup()     (Omniverse 自動呼叫)
  └─ on_shutdown()    (清理資源)

層 2️⃣ 服務層
  ├─ HTTP Handler (RANAPIHandler)
  ├─ WebSocket Server (ws_server.py)
  ├─ 命令隊列 (_enqueue + _process_commands)
  └─ USD 操作 (builder.move_ue, push_signal 等)

層 1️⃣ 傳輸層
  ├─ HTTP (port 8080)
  └─ WebSocket (port 8001 or dynamic)
```

---

## 📊 啟動流程：Clone 後的完整時間軸

### 前置條件

```bash
✓ ~/omniverse-env/bin/activate      (Python venv with omniverse-kit)
✓ scene_config.json                  (場景設定檔)
✓ DISPLAY 已設定                     (本地 X 或 VNC)
✓ /home/mitlab/Omniverse/kit-app-template/_build/...  (extscache)
```

### 啟動命令

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform
docker compose up -d                           # 啟動 Postgres + Django + Next.js

cd kit
source ~/omniverse-env/bin/activate
./run.sh                                       # 啟動 Kit（會卡在這，持續執行）
```

### 時間軸：T = 0 開始

```
T+0s
  $ ./run.sh
  └─ python -m omni.kit_app ran_server.kit

T+1-2s
  Omniverse Kit 核心初始化
  ├─ 讀取 ran_server.kit
  ├─ 解析 [dependencies] (50+ 個標準擴展)
  ├─ 應用 [settings]
  └─ 掃描擴展資料夾

T+3s
  ✅ 加載 #1: mitlab.ran.scene.builder
  ├─ 讀取 config/extension.toml
  ├─ import mitlab.ran.scene.builder
  ├─ 實例化 RANSceneBuilderExtension
  ├─ 呼叫 on_startup()
  │  ├─ 讀取 RAN_SCENE_CONFIG env
  │  ├─ 載入 scene_config.json
  │  └─ 準備場景資料
  └─ RANSceneBuilderExtension._instance = 單例

T+4s
  ✅ 加載 #2: mitlab.ran.api
  ├─ 讀取 config/extension.toml
  ├─ 檢查依賴：scene.builder ✓
  ├─ import mitlab.ran.api
  ├─ 實例化 RANAPIExtension
  ├─ 呼叫 on_startup()
  │  ├─ 初始化 _command_queue + _queue_lock
  │  ├─ 啟動 HTTPServer (port 8080)
  │  │  └─ 線程：daemon=True (背景執行)
  │  ├─ 訂閱 Kit 更新事件
  │  │  └─ get_update_event_stream().create_subscription_to_pop()
  │  ├─ 啟動 WebSocket Server
  │  │  └─ omni.kit.async_engine.run_coroutine(ws_server.serve())
  │  └─ 建立 UI 窗口
  │     └─ ui.Window("RAN API", width=280, height=80)
  └─ [stdout] "[mitlab.ran.api] HTTP :8080  WS :port"

T+5s
  ✅ 加載 #3: mitlab.ran.labels
  ├─ 讀取 config/extension.toml
  ├─ 檢查依賴：omni.ui, omni.kit.viewport ✓
  ├─ import mitlab.ran.labels
  ├─ 實例化 RANLabelsExtension
  ├─ 呼叫 on_startup()
  │  ├─ 訂閱 USD Tf.Notice (變更通知)
  │  ├─ 準備 2D 浮標渲染
  │  └─ 啟動事件監聽器
  └─ ✓ 就緒

T+6-10s
  Kit 主循環初始化
  ├─ 初始化 Vulkan 渲染器 (需要 GPU + DISPLAY)
  ├─ 建立空舞台 (/World)
  ├─ 啟動事件循環
  │  └─ 每幀 ~16.67ms (60 FPS)
  │     └─ 呼叫訂閱的回調
  │        └─ RANAPIExtension._process_commands()
  └─ VNC/X 視窗出現 (標題：「RAN Omniverse Server」)

T+10s+
  ✅✅✅ 完全就緒
  ├─ HTTP :8080 接收請求
  ├─ WebSocket 準備推送
  ├─ 命令隊列監聽
  └─ 場景已初始化
```

---

## 📡 Extension 之間的互動

### 1️⃣ scene.builder ← → api

```python
# api/extension.py 中，獲取 scene.builder 實例：
def _get_scene_builder(self):
    from mitlab.ran.scene.builder.extension import RANSceneBuilderExtension
    return RANSceneBuilderExtension._instance

# 為什麼能拿到？
# ✓ run.sh 裡 [dependencies] 保證 scene.builder 先加載
# ✓ scene.builder 在 on_startup() 裡設定了 _instance
# ✓ api 可以直接訪問單例
```

### 2️⃣ api ← → labels

```
labels extension 獨立監聽 USD 變更
  ├─ 訂閱 Tf.Notice（當 scene.builder 修改 USD 時自動觸發）
  └─ 不需要與 api 直接通信

優點：解耦 ✓
```

---

## 🔄 資料流示例：HTTP 請求「Move UE」

```
客戶端 (前端或 curl)
  │
  POST /ue/UE_1/move
  {"x": 100, "y": 50, "z": 200}
  │
  ▼ (層 1️⃣ 傳輸層)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HTTPServer port 8080 (背景線程)
  └─ RANAPIHandler.do_POST()
     ├─ 解析路徑：parts = ["ue", "UE_1", "move"]
     ├─ 驗證 action = "move"
     └─ 讀取 body: {"x": 100, "y": 50, "z": 200}

  │
  ▼ (層 2️⃣ 服務層 - 入隊)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
命令隊列（線程邊界）
  └─ _enqueue("move_ue", name="UE_1", x=100, y=50, z=200)
     ├─ 加鎖 (_queue_lock)
     ├─ append 到 _command_queue
     ├─ 解鎖
     └─ 立即返回 HTTP 200 {"status": "queued"}

  │
  ▼ (層 3️⃣ 框架層 - Kit 主循環)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kit 主循環（每幀 ~16.67ms）
  └─ _process_commands() (來自 update event subscription)
     ├─ 加鎖，複製隊列
     ├─ 解鎖，清空原隊列
     ├─ 取出命令：{"action": "move_ue", "name": "UE_1", ...}
     ├─ 呼叫 builder.move_ue(name="UE_1", x=100, y=50, z=200)
     │
     ▼ (層 2️⃣ 服務層 - 執行)
     ├─ 獲取 USD stage
     ├─ 找到 prim: /World/UE_1
     ├─ 修改 xformOp:translate = (100, 50, 200)
     └─ USD 變更觸發

  │
  ▼ (labels extension 自動反應)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
labels extension 監聽 Tf.Notice
  └─ 偵測 UE_1 位置變更
     └─ 更新浮標位置 (2D HUD)

  │
  ▼ (WebSocket 推送)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ws_server.py 推送新狀態
  └─ 所有連接的客戶端收到：
     {
       "type": "ue_update",
       "name": "UE_1",
       "position": {"x": 100, "y": 50, "z": 200}
     }

客戶端 (前端地圖立即更新)
VNC (3D 視圖立即顯示移動)

[整個過程耗時：~20-50ms]
```

---

## 🧵 線程模型：為什麼需要命令隊列

```
HTTP Server 線程 (多線程，BaseHTTPRequestHandler)
  ├─ 不能直接操作 USD (會 segfault)
  └─ 只能入隊

        ⬇️ (入隊：線程安全，有鎖)

命令隊列 (_command_queue + _queue_lock)
  ├─ 線程邊界
  ├─ 保護共享資源
  └─ 讓 USD 操作集中到單一線程

        ⬇️ (出隊：在 Kit 主線程)

Kit 主線程 (單線程，Omniverse event loop)
  ├─ 執行 _process_commands()
  ├─ 呼叫 builder.move_ue()
  ├─ 修改 USD stage
  └─ ✓ 安全

示意圖：
┌─────────────────┐
│ HTTP req 1      │  ┌──────────────────────┐
│ HTTP req 2  ───┼─→│ 命令隊列 + 鎖        │
│ HTTP req 3  ───┼─→│  ↓ (出隊每幀 1 次)  │
└─────────────────┘  └──────────────────────┘
(多線程，不安全)          (線程邊界)
                            ⬇️
                    ┌──────────────────────┐
                    │ Kit 主線程           │
                    │ USD 操作（安全）     │
                    └──────────────────────┘
                    (單線程)
```

---

## ✅ 啟動驗證清單

### 1️⃣ 檢查 Docker 容器

```bash
$ docker ps
CONTAINER ID   IMAGE              STATUS
xxx            omniver_postgres   Up 2 minutes
xxx            omniver_backend    Up 2 minutes
xxx            omniver_frontend   Up 2 minutes
```

### 2️⃣ 檢查 Kit 日誌

```bash
# Terminal 執行 ./run.sh 的地方，應該看到：
[mitlab.ran.scene.builder] Extension startup
[mitlab.ran.api] Extension startup
[mitlab.ran.api] HTTP :8080  WS :8001
[mitlab.ran.labels] Extension startup
```

### 3️⃣ 驗證 HTTP API

```bash
$ curl http://localhost:8080/
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
```

### 4️⃣ 驗證 Django 後端

```bash
$ curl -X POST http://localhost:8001/api/v0.1/RAN/Scene/SceneStateReader/read \
  -H "Content-Type: application/json" -d '{}'

{
  "success": true,
  "data": {
    "buildings": 6,
    "gnbs": 3,
    "ues": 5,
    "animating": false
  }
}
```

### 5️⃣ 驗證前端

```bash
$ curl -I http://localhost:3001
HTTP/1.1 200 OK
```

### 6️⃣ VNC/X 視窗驗證

- 應該看到：「RAN Omniverse Server」視窗
- 右側有：「RAN Scene Builder」和「RAN API」面板
- 3D 視圖：空白舞台（沒建場景前）

### 7️⃣ 建構場景

在 VNC 視窗點擊「RAN Scene Builder」面板中的「Build Scene」

```bash
# 或用 curl
$ curl -X POST http://localhost:8080/scene/build
{"status": "queued"}

# 檢查狀態
$ curl http://localhost:8080/scene/status
{
  "buildings": 6,
  "gnbs": 3,
  "ues": 5,
  "animating": false
}
```

VNC 3D 視圖應該顯示場景（建築物、基站、UE）。

---

## 🔧 開發與除錯

### 查看日誌

```bash
# Kit 日誌（控制台）
# 看 [mitlab.ran.*] 的訊息

# Django 日誌
$ docker logs omniver_backend -f

# 前端日誌
$ docker logs omniver_frontend -f
```

### 修改代碼後重新加載

```bash
# Extension 代碼修改 → Kit 需要重啟
cd kit && source ~/omniverse-env/bin/activate && ./run.sh

# Django/Next.js → 自動 reload (development)
```

### 調試命令隊列

在 `api/extension.py` 中加入日誌：

```python
def _process_commands(self, event):
    with self._queue_lock:
        if not self._command_queue:
            return
        cmds = list(self._command_queue)
        self._command_queue.clear()
    
    print(f"[RAN API] Processing {len(cmds)} commands")  # ← 添加此行
    
    for cmd in cmds:
        action = cmd.get("action")
        print(f"[RAN API] Executing: {action}")  # ← 添加此行
        ...
```

重啟 Kit 查看日誌。

---

## 📚 Extension 詳細說明

### 1️⃣ mitlab.ran.scene.builder

**職責：**
- 讀取 scene_config.json 場景設定
- 建構 3D 場景（建築、基站、UE）
- 管理動畫（UE 軌跡）
- 提供單例讓 api 層訪問

**主要方法：**
```python
_build_scene()           # 根據 config 建構場景
move_ue(name, x, y, z)  # 移動 UE
push_signal(...)        # 推送 RF 信號屬性
update_trajectory(...)  # 更新 UE 動畫軌跡
update_gnb(...)         # 更新基站參數
```

**關鍵設計：**
- 單例模式：`_instance` 讓其他 extension 訪問
- 配置驅動：場景由 JSON 定義，無需改代碼

---

### 2️⃣ mitlab.ran.api

**職責：**
- HTTP REST API (port 8080)
- WebSocket 推送 (動態 port)
- 命令隊列 (HTTP → USD 的橋樑)

**主要方法：**
```python
do_GET()             # GET /scene/status, /gnbs, /ues 等
do_POST()            # POST /scene/build, /ue/{name}/move 等
_enqueue(action, **) # 線程安全入隊
_process_commands()  # 在 Kit 主線程執行
```

**HTTP 端點：**
| 方法 | 路徑 | 功能 |
|-----|------|------|
| GET | /scene/status | 場景狀態（建築、gNB、UE 數量）|
| GET | /gnbs | 列出所有基站 |
| GET | /gnb/{name} | 特定基站詳情 |
| GET | /ues | 列出所有 UE |
| GET | /ue/{name} | 特定 UE 詳情 |
| GET | /scene/layout | 完整佈局（前端地圖用）|
| POST | /scene/build | 建構場景 |
| POST | /scene/clear | 清空場景 |
| POST | /animation/start | 啟動動畫 |
| POST | /animation/stop | 停止動畫 |
| POST | /ue/{name}/move | 移動 UE |
| POST | /ue/{name}/trajectory | 更新軌跡 |
| POST | /ue/{name}/signal | 推送信號 |
| POST | /gnb/{name}/update | 更新基站 |

---

### 3️⃣ mitlab.ran.labels

**職責：**
- UE 頭上浮標（2D HUD）
- 顯示 RSRP/SINR 數值
- 事件驅動：只在 UE/gNB 變更時更新

**主要設計：**
- 訂閱 USD Tf.Notice（變更通知）
- 不主動輪詢，降低 CPU 占用

---

## 🎯 常見問題

### Q: 為什麼需要三個 extension，不能合為一個？

**A:** 分離關注點的最佳實踐。
- 通信層 (api) 與數據層 (builder) 分離 → 易於測試、易於維護
- 可獨立開發、獨立測試
- 降低耦合

### Q: HTTP 請求為什麼要入隊，不能直接修改 USD？

**A:** USD 不是線程安全的。
- HTTP server 在多線程運行
- 直接修改 USD 會 segfault
- 命令隊列是唯一安全的跨線程邊界方式

### Q: WebSocket 有什麼用？

**A:** 實時推送，比 HTTP 輪詢高效。
- HTTP：客戶端問、伺服器答（同步）
- WebSocket：伺服器主動推送（非同步）
- 低延遲、高效率

### Q: 如何快速切換不同的場景？

**A:** 修改 `scene_config.json`，重新調用 `/scene/clear` + `/scene/build`。
無需改代碼！

### Q: 為什麼 VNC 只看到 Omniverse 窗口，看不到整個伺服器？

**A:** Xvfb 虛擬顯示 + x11vnc 綁定特定顯示。
- `DISPLAY :88` → 虛擬螢幕
- x11vnc 只投影 `:88`
- 整個伺服器的其他應用看不到

---

## 📖 相關檔案

| 檔 | 位置 | 用途 |
|----|------|------|
| run.sh | ../kit/ | Kit 啟動腳本 |
| ran_server.kit | ../kit/ | Kit 應用設定 (.kit 格式) |
| scene_config.json | ../../ | 場景設定 (JSON) |
| docker-compose.yml | ../../ | Docker 容器設定 |
| backend_rule.md | ../../ | Django 架構規範 |
| frontend_rule.md | ../../ | Next.js 架構規範 |

---

## 🚀 快速開始

```bash
# 1. Clone & 進入項目
cd /home/mitlab/XAPP_DT/Omnivers_platform

# 2. 啟動 Docker
docker compose up -d

# 3. 啟動 Kit
cd kit
source ~/omniverse-env/bin/activate
./run.sh &

# 4. 等待 10 秒，然後驗證
sleep 10
curl http://localhost:8080/scene/status

# 5. 打開前端
open http://localhost:3001

# 6. 在 VNC 點擊「Build Scene」
```

完成！🎉

---

## 📝 更多資源

- [Omniverse Kit 官方文檔](https://docs.omniverse.nvidia.com/kit/docs/index.html)
- [USD 官方文檔](https://graphics.pixar.com/usd/docs/index.html)
- 本項目的 `docs/` 目錄（時序圖、煙霧測試腳本等）
