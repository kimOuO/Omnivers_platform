# Kit Internals 101 — Omniver Platform 核心運作筆記

> 給你從零到懂「Kit 怎麼被我們驅動」的一份精簡筆記。依初學順序編排，前面看懂才看後面。

---

## 📚 目錄（建議閱讀順序）

1. [大局觀：4 個 process 是誰](#1-大局觀4-個-process-是誰)
2. [Kit 是什麼？Extension 是什麼？](#2-kit-是什麼extension-是什麼)
3. [三個 Extension 的職能分配](#3-三個-extension-的職能分配)
4. [`on_startup` 是什麼](#4-on_startup-是什麼)
5. [外部請求怎麼進來](#5-外部請求怎麼進來)
6. [Queue 是什麼？為什麼需要](#6-queue-是什麼為什麼需要)
7. [Lock 與 Thread 角色](#7-lock-與-thread-角色)
8. [事件 (event) 與幀 (frame) 的關係](#8-事件-event-與幀-frame-的關係)
9. [兩種訂閱是什麼](#9-兩種訂閱是什麼)
10. [完整走一遍：前端改軌跡 → VNC 看到 UE 改走](#10-完整走一遍前端改軌跡--vnc-看到-ue-改走)
11. [Thread / Port 速查表](#11-thread--port-速查表)
12. [常用白話類比](#12-常用白話類比)

---

## 1. 大局觀：4 個 process 是誰

```
┌───────── Host (筆電，有 GPU + VNC) ────────────────────────┐
│                                                             │
│   Kit Render Server            host 上直接跑，不裝 docker    │
│   :8080 (HTTP) + VNC display                                │
│                                                             │
│   ┌──── Docker 網路 ─────────────────────────────────────┐  │
│   │                                                      │  │
│   │   Postgres   :5432                                   │  │
│   │   Django     :8001 → 容器內 :8000                     │  │
│   │   Next.js    :3001 → 容器內 :3000                     │  │
│   │                                                      │  │
│   └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ↑                                        ↑
       browser                              external RAN sim
  (打 :3001 看前端                       (未接入；未來透過
   + 打 :8001 打 API)                       :8001 ingest 訊號)
```

**記一個口訣**：**3 個 docker + 1 個 host = 4 個 process**。

- **Kit** 在 host 的原因：要 GPU、Vulkan、VNC display，進 container 會很麻煩
- **Django/Postgres/Next.js** 在 docker 的原因：純軟體、好部署、好隔離

---

## 2. Kit 是什麼？Extension 是什麼？

**Kit** = NVIDIA 的 3D engine runtime（類似遊戲引擎）。你執行 Kit 這個大程式之後，它會：

1. 讀一個 `.kit` 設定檔
2. 依設定載入一堆 Python 模組（叫 extension）
3. 呼叫它們的 `on_startup`
4. 進入 render loop（每秒畫 60 幀）

**Extension** = 你寫的 Python module + 設定檔。每個 extension 就是一個「Kit 的插件」。

### 類比

```
Kit             = 瀏覽器 (Chrome)
Extensions      = 擴充套件 (廣告攔截、密碼管理器)
ran_server.kit  = 瀏覽器 profile (指定要啟用哪些擴充套件)
```

### 實際檔案長哪樣

```
Omniver_platform/
├── kit/
│   ├── ran_server.kit    ← Kit 的設定檔 (TOML)
│   └── run.sh             ← 啟動 Kit 的 shell script
│
└── extensions/
    ├── mitlab.ran.scene.builder/
    │   ├── config/extension.toml   ← extension 自己的 metadata
    │   └── mitlab/ran/scene/builder/extension.py   ← 主程式
    ├── mitlab.ran.api/
    └── mitlab.ran.labels/
```

**啟動順序**：
```
./run.sh
  → python -m omni.kit_app ran_server.kit
  → Kit 讀 ran_server.kit 裡的 [dependencies]
  → Kit 掃 extensions/ 找到對應 extension
  → Kit 每一個都 import，呼叫 on_startup()
```

---

## 3. 三個 Extension 的職能分配

| Extension | 定位 | 核心職責 |
|---|---|---|
| **`mitlab.ran.scene.builder`** | 場景工頭 | 讀 `scene_config.json`、在 USD stage 建物件（建築/gNB/UE）、每幀挪動 UE（動畫）、提供 UI 按鈕 |
| **`mitlab.ran.api`** | 門口接線生 | 跑一個 HTTP server (port 8080)、把外部請求轉成「命令」塞進 queue、每幀從 queue 取出命令呼叫 builder |
| **`mitlab.ran.labels`** | 資訊看板畫師 | 每幀讀 UE 身上的 `ran:*` custom attribute (RSRP、SINR)、在 UE 頭上畫浮字 |

### 依賴方向

```
api 匯入 scene.builder 的 class (用 ._instance 取到物件)
labels 也可以讀 scene.builder 的 _config
scene.builder 不認識 api，也不認識 labels   (單向依賴)
```

**好處**：`api` 關掉、`labels` 關掉，`scene.builder` 照樣能用（UI 按鈕還在）。

---

## 4. `on_startup` 是什麼

**`on_startup` = Kit 叫你的 extension「開機」時呼叫的函式**。

```python
import omni.ext

class MyExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        # Kit 啟動時呼叫一次
        # 這裡寫你要初始化的東西
        # (開 HTTP server、訂閱 event、建 UI 窗...)
        pass

    def on_shutdown(self):
        # Kit 關閉時呼叫一次
        # 這裡清理資源 (關 server、取消訂閱...)
        pass
```

### 為什麼需要

Kit 光 `import` 你的模組**不會自動跑你的邏輯**。它要你在 `on_startup` 裡**明確寫**「啟動要做什麼」。沒寫 `on_startup` = extension 什麼都不做。

### 類比

- **Django** 的 `AppConfig.ready()`
- **React** 的 `useEffect(() => { /* mount */; return () => { /* unmount */ } }, [])`

---

## 5. 外部請求怎麼進來

```
curl / 前端 fetch
   │
   │ HTTP :8080
   ▼
[Kit process]
   │
   │ HTTP thread (serve_forever)
   │   do_POST() 解析 URL + body
   │   → 把指令包成 dict 塞進 queue:
   │      {"action": "update_trajectory", "name": "UE_1",
   │       "waypoints": [[0,0,0],[50,0,50]], ...}
   │   → 立刻 return HTTP 200 {"status":"queued"}
   │
   │ ← HTTP thread 工作完畢
   │
   │ .......等 ~16 ms（下一幀到來）.......
   │
   │ Main thread (跑 render loop)
   │   Kit 發 update event
   │   api ext 的 _process_commands 被叫
   │   → with lock: 取出 queue 裡所有命令
   │   → for cmd in cmds: 依 action 分派
   │      → builder.update_trajectory(...)
```

**關鍵概念**：HTTP thread 不碰 USD，只負責**把意圖寫成 dict 塞 queue**。下一幀 main thread 才真正執行。

---

## 6. Queue 是什麼？為什麼需要

### Queue = 待辦清單

```python
self._command_queue = []   # 就一個 Python list

# 塞 (producer)
self._command_queue.append({"action": "move_ue", "name": "X", ...})

# 取 (consumer)
cmds = list(self._command_queue)
self._command_queue.clear()
for cmd in cmds: ...
```

### 為什麼需要

**硬限制**：USD stage 只能在 **Kit 主執行緒**改，背景執行緒改會 crash。

**我們的情境**：
- HTTP thread 隨時進來 → 跑在背景
- 但不能直接改 USD

**解法**：HTTP thread 只把「想做什麼」寫進 queue。主執行緒每幀才真正取出來執行。

```
外部 thread 想改 USD ─X─→ 直接改會 crash
外部 thread 塞 queue ─✓─→ 主執行緒排隊取出改
```

### 實戰中的命令範例

```python
# 移動 UE 到指定座標
{"action": "move_ue", "name": "UE_1", "x": 10, "y": 0, "z": 20}

# 更新 UE 走的軌跡
{"action": "update_trajectory", "name": "UE_1",
 "waypoints": [[0,0,0],[50,0,50]], "speed_mps": 3.0, "loop": True}

# 推訊號進場域
{"action": "push_signal", "name": "UE_1",
 "serving_cell": "gNB_Macro_NW", "rsrp_dbm": -78.2, "sinr_db": 12.5}

# 場景控制
{"action": "build_scene"}
{"action": "clear_scene"}
{"action": "start_animation"}
```

---

## 7. Lock 與 Thread 角色

### 兩個會碰 queue 的角色

| Thread | 誰在跑 | 頻率 |
|---|---|---|
| **HTTP thread** | `mitlab.ran.api` 啟的背景 thread（跑 `HTTPServer.serve_forever`） | 有請求才動 |
| **Main thread** | Kit 主執行緒（render loop） | 每幀 ~16 ms |

### 為什麼要鎖

光 `append` 一個動作是 thread-safe（CPython GIL 保護）。但 main thread 做的是**複合操作**：

```python
cmds = list(self._command_queue)   # ① 複製
self._command_queue.clear()         # ② 清空
```

這兩步中間如果 HTTP thread 剛好 `append`，那筆命令會**被清掉**（永遠消失）。

**Lock 保證這段程式碼不會被打斷**：

```python
with self._queue_lock:
    cmds = list(self._command_queue)
    self._command_queue.clear()
# ↑ 這整段鎖起來，HTTP thread 要 append 會等鎖開
```

### 類比

- **鎖** = 拿麥克風。拿到的人講完才換下一個。
- **沒鎖** = 大家搶著講，句子都被蓋掉變亂碼。

### 附註：ThreadingHTTPServer

目前我們用的是**單執行緒 HTTPServer**（一次只處理一個 HTTP 請求）。如果改用 `ThreadingHTTPServer`，每個 HTTP 請求會各開一個 thread，同時可能有 N 個 HTTP thread 寫 queue。Lock 讓我們未來擴充時不用改。

---

## 8. 事件 (event) 與幀 (frame) 的關係

### 一幀 = 一次 event

Kit 的 render loop 每 **~16 ms**（60 FPS）做一個循環，**每次循環開頭發一個 event**。

```
時間:   0ms    16ms   32ms   48ms   64ms  ...
幀號:    #1     #2     #3     #4     #5
event:  ●      ●      ●      ●      ●
        ↓      ↓      ↓      ↓      ↓
      所有訂閱者被呼叫
        ↓      ↓      ↓      ↓      ↓
      渲染   渲染   渲染   渲染   渲染
```

### event 攜帶什麼

```python
event.payload = {
    "dt": 0.01687,    # 上一幀到這一幀經過的秒數（delta time）
    "frame": 12345,   # 目前第幾幀
    # ...
}
```

**最常用是 `dt`**。例如動畫：
```python
ue["dist"] += ue["speed"] * dt
# 速度 3 m/s × 0.016 s = 0.048 m / 幀
# 這幀 UE 要挪 0.048 公尺
```

用 `dt` 的好處：FPS 高（dt 小）每幀挪少一點，FPS 低（dt 大）每幀挪多一點，**總速度跟 FPS 無關**。

### 動畫 ≠ 一次 event，而是「每幀各一次 event」

```
一段 10 秒的動畫 = 60 FPS × 10 s = ~600 次 event
每次 event callback 挪一小步 (0.048 m)
加起來 UE 走了 3 m/s × 10 s = 30 m
```

---

## 9. 兩種訂閱是什麼

### 訂閱 = 告訴 Kit「每幀叫我」

```python
import omni.kit.app

sub = omni.kit.app.get_app() \
    .get_update_event_stream() \
    .create_subscription_to_pop(my_callback, name="...")
#         ↑              ↑              ↑               ↑
#       Kit 的 app     事件流 (每幀發)  要叫的函式     名字 (debug 用)
```

- **sub 物件要存成 self 變數**，不然會被 Python GC → 訂閱失效
- `sub = None` → 取消訂閱

### 類比

- 訂 YouTube 頻道：頻道發新片會通知你
- 訂 update stream：Kit 每幀會叫你一次

### 我們平台的兩種訂閱

```
                    ┌──► _process_commands   (api 的訂閱 A)
Kit update stream ──┼──► _on_animation_update (builder 的訂閱 B)
   每 ~16ms 發一次    └──► labels.invalidate    (labels 的訂閱 C)
```

#### 訂閱 A：**處理 queue**（`mitlab.ran.api`）
- 每幀被叫 → 看 queue 有沒有外部命令 → 有就分派
- **借 Kit 每幀 event 當主執行緒入口**（解決跨執行緒的 race）
- 命令空就直接 return（便宜）

#### 訂閱 B：**推進動畫**（`mitlab.ran.scene.builder`）
- 每幀被叫 → 掃 `_animated_ues` → 用 dt 挪每個 UE 一點點
- **這個訂閱不碰 queue**（沒有跨執行緒問題；Kit 自己叫自己）
- 按 ▶ Start Animation 才訂閱；按 ■ Stop 就取消

#### 訂閱 C：**重繪文字**（`mitlab.ran.labels`）
- 每幀被叫 → 重畫 UE 頭上浮字（讀 USD custom attr）

### 為什麼拆三個訂閱？

**各司其職**：
- `api` 不懂動畫
- `scene.builder` 不懂 HTTP
- `labels` 不懂資料從哪來

每個 extension 自己訂閱自己需要的，**任何一個停掉都不影響其他**。

---

## 10. 完整走一遍：前端改軌跡 → VNC 看到 UE 改走

```
前端按 [Apply]
  │
  │ POST http://localhost:8001/api/v0.1/RAN/UE/UEController/trajectory
  │ body: {name:"UE_1", waypoints:[[0,0,0],[50,0,50]], speed_mps:3.0, loop:true}
  ▼
Django (docker container)
  │ 1. Actor UEController.trajectory 接收
  │ 2. Serializer 驗證
  │ 3. upsert DB (ue_config)
  │ 4. 打 Kit: POST http://host.docker.internal:8080/ue/UE_1/trajectory
  ▼
Kit (host)
  │ [HTTP thread] do_POST() 收到
  │   └─ _enqueue("update_trajectory", ...)      ← 命令進 queue
  │   └─ return {"status":"queued"}              ← 立刻回 HTTP
  │
  │ ...等 <16ms，下一幀...
  │
  │ [Main thread] update event 發送
  │   └─ _process_commands(event)                ← api 訂閱 A 被叫
  │        └─ cmds 從 queue 取出                 ← 帶 lock
  │        └─ builder.update_trajectory(...)     ← 改 _animated_ues
  │
  │   └─ _on_animation_update(event)             ← builder 訂閱 B 被叫
  │        └─ 讀 _animated_ues (已經是新路徑)
  │        └─ 算出新位置
  │        └─ 寫 USD: UE_1.translate = (...)     ← 改 stage
  │
  │   └─ labels invalidate                       ← labels 訂閱 C 被叫
  │        └─ 重畫 UE 頭上浮字
  │
  │ [Main thread] Hydra 渲染當幀
  │        └─ 讀 USD → 畫 frame → VNC 顯示
  ▼
你看到 UE_1 開始走新路
```

### 關鍵記憶

| 概念 | 含意 |
|---|---|
| **命令只經 queue 一次** | 新軌跡**一次性**進 queue，被 `_process_commands` 執行，改 `_animated_ues`。之後 600 幀動畫都直接讀這個 list，不再進 queue |
| **訂閱是每幀都呼叫** | 不管有沒有新命令、有沒有動畫，訂閱就是持續每幀叫 |
| **同幀執行順序** | `_process_commands` → `_on_animation_update` → `labels` → 渲染。所以新命令**當幀就生效**（不用等下一幀） |

---

## 11. Thread / Port 速查表

### 啟動 Kit 後的 thread

| Thread | 用途 | 狀態 |
|---|---|---|
| **Kit main thread** | render loop、USD 操作、每幀發 event | 一直跑 |
| **HTTP serve_forever thread** | `mitlab.ran.api` 接 HTTP 請求 | 閒置等連線 |
| (內部) Kit 還有一堆 worker thread | 資源載入、網路 I/O 等 | Kit 自己管 |

**簡化記**：跟我們有關的是 **2 個 thread**（main + HTTP）。

### Port 全表

| Process | Port | 誰聽 | 給誰打 |
|---|---|---|---|
| Kit Render Server | **8080** | Kit HTTP server (api ext) | Django (透過 `host.docker.internal:8080`) |
| Django Backend | **8001** (外) / 8000 (內) | docker container 內 gunicorn/runserver | Browser、external RAN sim |
| Next.js Frontend | **3001** (外) / 3000 (內) | docker container 內 Next.js dev server | Browser |
| PostgreSQL | **5432** | docker container | Django |
| VNC display | (非 HTTP) | X server 或 VNC 的 `:0` / `:1` | Kit 用來畫 viewport |

---

## 12. 常用白話類比

| 概念 | 類比 |
|---|---|
| Kit | 容器（像瀏覽器） |
| Extension | 擴充套件（像瀏覽器 ad blocker） |
| `.kit` 檔 | 瀏覽器 profile（指定載哪些擴充） |
| `on_startup` | 員工報到第一天 — 主管交代要做什麼 |
| `on_shutdown` | 下班前關燈鎖門 |
| Update event stream | 公寓管委會每早 07:00 廣播 |
| 訂閱 | 你對廣播有興趣，登記住址 |
| Main thread | 快遞員（每 16ms 回公司一次收件） |
| HTTP thread | 客服（接電話只負責記下訂單） |
| Queue | 辦公室的待寄包裹堆 |
| Lock | 搶麥克風前要排隊 |
| USD stage | 公司的貨倉（只有快遞員有權限進） |
| 動畫 | 每天持續做的家事（澆花、擦窗） |
| Custom attribute | 包裹上貼的便條紙（訊號值用它存） |

---

## 📍 你最少要記的 5 件事

1. **Kit 是容器，我們寫 3 個 extension 塞進去**（scene.builder / api / labels）
2. **`on_startup` = Kit 叫你開機；裡面寫初始化**
3. **USD 只能在 main thread 改**；外部 HTTP 進來的請求要透過 queue 排隊
4. **訂閱 update stream** = 註冊「每幀 Kit 叫我」的 callback；我們有兩種用途：
   - **處理 queue**（api 的訂閱）
   - **推進動畫**（builder 的訂閱）
5. **事件 = 每幀一次**；動畫就是「600 次 event 累積出來的大挪移」

---

## 🎯 往下可以深究

- **最小 extension 範例**（10 行寫一個 on_startup + 訂閱）
- **USD prim / attribute 樹狀結構**（prim 是節點、attribute 是屬性）
- **Kit 的 `omni.ui.scene`**（我們 labels 用來畫 3D 文字的 API）
- **Django backend 的 Actor / Serializer / Service 分層**（依 `backend_rule.md`）
- **Next.js App Router 的 app / components / hooks / services 白名單**（依 `frontend_rule.md`）

這些在 `docs/` 其他文件裡也有，需要哪個我再延伸。
