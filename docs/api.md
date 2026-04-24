# Omniver Platform — Backend API

Base URL：`http://localhost:8001`（container 內 `omniver_backend:8000`）

## 通用規則

- **全部是 POST**，即使「讀」也是 POST（backend_rule.md §7-2）
- URL 格式：`/api/v0.1/RAN/{Module}/{Actor}/{Element}`
- Content-Type：`application/json`
- 統一 response envelope：

```json
{
  "success": true,
  "message": "OK",
  "data":    { ... },
  "errors":  { ... }     // 只在 success=false 出現
}
```

---

## 1. Scene（場景控制）

| API | Input (body) | Output (`data`) | 目的 |
|---|---|---|---|
| `POST /api/v0.1/RAN/Scene/SceneStateReader/read` | `{}` | `{buildings: int, gnbs: int, ues: int, animating: bool}` | 看場景一句話摘要（數量 + 動畫狀態），Dashboard status bar 吃這支。proxy 打 Kit `/scene/status` |
| `POST /api/v0.1/RAN/Scene/SceneLayoutReader/read` | `{}` | `{buildings: [...], gnbs: [...], ues: [...], ground: {...}}` 完整陣列 | **靜態場景資料** — buildings/gnbs 座標+屬性。前端 Dashboard 的 gNB 表格、Trajectory 的 SVG 地圖、Signals 頁的 UE 下拉都靠這個。proxy 打 Kit `/scene/layout` |
| `POST /api/v0.1/RAN/Scene/SceneController/build` | `{}` | `{action: "build"}` | 告訴 Kit「把 USD 場景建起來」（讀 scene_config.json → 生建築/gNB/UE prim）。non-blocking：Kit 把工作排到 main-thread 的 update tick 上處理 |
| `POST /api/v0.1/RAN/Scene/SceneController/clear` | `{}` | `{action: "clear"}` | 清空整個 `/World/*`，回到空場景 |
| `POST /api/v0.1/RAN/Scene/AnimationController/start` | `{}` | `{action: "start"}` | 啟動 UE 沿 waypoints 自動跑動畫 |
| `POST /api/v0.1/RAN/Scene/AnimationController/stop` | `{}` | `{action: "stop"}` | 停止動畫，UE 停在當前位置 |

---

## 2. UE（使用者設備）

| API | Input (body) | Output (`data`) | 目的 |
|---|---|---|---|
| `POST /api/v0.1/RAN/UE/UEReader/read` | `{}` | `[{name, position:{x,y,z}, serving_cell, rsrp_dbm, sinr_db}, ...]` | 拿所有 UE 當下狀態（一次性、HTTP fallback 用；即時靠 WebSocket） |
| `POST /api/v0.1/RAN/UE/UEController/move` | `{name: str, x: num, z: num, y?: num}` | `{name, x, y, z}` | 把 UE 瞬移到指定座標（測試、debug 用） |
| `POST /api/v0.1/RAN/UE/UEController/trajectory` | `{name: str, waypoints: [[x,y,z], ...], speed_mps: num, loop?: bool}` 至少 2 個點 | `{name, waypoints_count}` | 指定 UE 的動畫軌跡（Trajectory Editor 按 Apply 就打這個）。`loop=true` 是 ping-pong 來回 |

---

## 3. gNB（基地台）

| API | Input (body) | Output (`data`) | 目的 |
|---|---|---|---|
| `POST /api/v0.1/RAN/GNB/GNBReader/read` | `{}` | `[{name, position, freq_mhz, power_dbm, bw_hz, active}, ...]` | 拿所有 gNB 設定 |
| `POST /api/v0.1/RAN/GNB/GNBController/update` | `{name: str, power_dbm?: num, active?: bool}` | `{name}` | 改 gNB 功率 / 啟停（目前 Kit 只收到不會真的改，stub） |

---

## 4. Ingest（入口 — 給外部系統寫資料）

| API | Input (body) | Output (`data`) | 目的 |
|---|---|---|---|
| `POST /api/v0.1/RAN/Ingest/SignalIngestor/create` | `{ts?: ISO string, signals: [{ue_name, serving_cell, rsrp_dbm, sinr_db, rsrp_map: {gnb: rsrp}}]}` | `{accepted: int, kit_errors: int}` | **外部訊號模擬器**（Sionna / ranp-sim）把算好的 RSRP/SINR push 進來。3 件事：① 寫 `signal_history` 時序 ② upsert `ue_state` 最新快照 ③ 同步轉發給 Kit 更新 UE billboard |
| `POST /api/v0.1/RAN/Ingest/SceneIngestor/create` | `{scene_id: str, buildings?: [], gnbs?: [], ues?: []}` | `{scene_uuid, scene_id}` | 把外部給的場景設定存進 `scene_snapshot` + upsert gNB configs（冷啟動 / 重跑實驗用） |

---

## 5. History（時序查詢）

| API | Input (body) | Output (`data`) | 目的 |
|---|---|---|---|
| `POST /api/v0.1/RAN/History/PositionHistoryReader/read` | `{ue_name: str, since?: "-5m"\|"-15m"\|"-1h" 或 ISO}` | `[{ts, x, y, z}, ...]` | 看某 UE 過去一段時間的移動軌跡（dev 可用來回放） |
| `POST /api/v0.1/RAN/History/SignalHistoryReader/read` | `{ue_name: str, since?: "-5m"\|...}` | `[{ts, serving_cell, rsrp_dbm, sinr_db, rsrp_map}, ...]` | Signal History 頁面畫 RSRP / SINR 時序圖的資料源 |

`since` 支援相對字串（`-5m`, `-15m`, `-30m`, `-1h`）或 ISO 8601 時間戳

---

## 6. Platform（事件記錄）

| API | Input (body) | Output (`data`) | 目的 |
|---|---|---|---|
| `POST /api/v0.1/RAN/Platform/PlatformReporter/create` | `{event: str, payload: object}` | `{event_uuid}` | 把「外部平台關心的事件」記一筆進 `platform_event`（stub，未來對接真平台用） |

---

## 7. WebSocket — 即時串流

| Endpoint | Direction | Message | 目的 |
|---|---|---|---|
| `ws://localhost:8001/api/v0.1/RAN/UE/live` | Server → Client | 連上先收 `{type:"hello", group:"ue_live"}`；之後每 500ms 收 `{type:"ue_update", ts, ues: [...]}` | **即時 UE snapshot 串流**。前端 Dashboard / Trajectory 的 UE 位置、serving cell、訊號 都靠這條。資料源是 Kit `:8081` 推過來的，backend 拿到就轉發 |

Client 只能「訂閱」不能 send（有 send 也被忽略）。

---

## 資料類型速查

**UE** 物件
```json
{
  "name": "UE_Handover_Path",
  "position": {"x": 22.0, "y": 0.0, "z": -22.0},
  "serving_cell": "gNB_Macro_NW",   // 可能為 null（還沒 ingest）
  "rsrp_dbm": -78.0,                 // 可能為 null
  "sinr_db": 12.0                    // 可能為 null
}
```

**gNB** 物件
```json
{
  "name": "gNB_Macro_NW",
  "position": {"x": -90.0, "y": 30.0, "z": 90.0},
  "freq_mhz": 3500.0,
  "power_dbm": 43.0,
  "bw_hz": 100000000.0,
  "active": true
}
```

**Building** 物件
```json
{
  "name": "Office_NW",
  "position": {"x": -50.0, "y": 0.0, "z": 50.0},
  "size": {"x": 30.0, "y": 25.0, "z": 30.0},
  "material": "concrete"
}
```

---

## Error responses

| HTTP | 常見情境 | body |
|---|---|---|
| 400 | JSON 格式錯 / 欄位缺 / 型別不對 | `{success:false, message:"Validation failed", errors:{...}}` |
| 404 | 找不到資源（gNB name 不存在、Coverage 沒建過…） | `{success:false, message:"gNB 'X' not found"}` |
| 408 | (frontend 自己的) 10s AbortController 超時 | — |
| 422 | `since` 時間格式無效 | `{success:false, message:"..."}` |
| 502 | Kit 離線 / 沒回應 | `{success:false, message:"Kit unreachable", errors:{detail:"..."}}` |

---

## 對照：誰會打什麼

| 角色 | 會打 |
|---|---|
| 前端 Dashboard 頁 | `SceneStateReader/read` × 1s、`SceneLayoutReader/read` × 1（mount）、**WS** 長連線 |
| 前端 Trajectory 頁 | `SceneLayoutReader/read` × 1、`UEController/trajectory`（按 Apply）、**WS** 長連線 |
| 前端 Signal History 頁 | `SignalHistoryReader/read` × 5s |
| 外部 Sionna / ranp-sim | `SignalIngestor/create` × N（算一次推一次） |
| 場景載入工具 | `SceneIngestor/create` × 1（冷啟動） |
| Scene Control 按鈕 | `SceneController/build` ∕ `clear`、`AnimationController/start` ∕ `stop`、`UEController/move` |

---

## 快速測試

訊號 ingest（模擬 Sionna 推一筆）
```bash
curl -X POST http://localhost:8001/api/v0.1/RAN/Ingest/SignalIngestor/create \
  -H "Content-Type: application/json" \
  -d '{"signals":[
    {"ue_name":"UE_Handover_Path","serving_cell":"gNB_Macro_NW",
     "rsrp_dbm":-78,"sinr_db":12,
     "rsrp_map":{"gNB_Macro_NW":-78,"gNB_Macro_SE":-92,"gNB_Small_Plaza":-85}}
  ]}'
```

查 UE 訊號時序
```bash
curl -X POST http://localhost:8001/api/v0.1/RAN/History/SignalHistoryReader/read \
  -H "Content-Type: application/json" \
  -d '{"ue_name":"UE_Handover_Path","since":"-15m"}'
```

套用軌跡
```bash
curl -X POST http://localhost:8001/api/v0.1/RAN/UE/UEController/trajectory \
  -H "Content-Type: application/json" \
  -d '{"name":"UE_Handover_Path","waypoints":[[0,0,0],[20,0,-20],[0,0,-40]],"speed_mps":3.0,"loop":true}'
```
