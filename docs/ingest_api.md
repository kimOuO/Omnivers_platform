# Ingest API Contract

**給**：外部系統（RAN 模擬器 / Sionna DU / ranp-sim / 場景工具）要打 Omniver-RAN 後端的實作者
**版本**：v0.1 — **更新日期**：2026-04-22

| 項目 | 值 |
|---|---|
| Base URL | `http://<host>:8001` |
| URL 格式 | `/api/v0.1/{System}/{Module}/{Component}/{Element}` |
| HTTP method | **POST**（backend_rule.md §7-2，全 POST）|
| Content-Type | `application/json` |
| 回應 envelope | `{ "success": bool, "message": str, "data": any, "errors"?: object }` |
| 認證 | 無（內網 demo）；正式需加 API key / mTLS |

---

## 1. 端點總表

| # | Module | Component / Element | 方向 | 用途 | 呼叫頻率 |
|---|---|---|---|---|---|
| 1.1 | Ingest | SignalIngestor/create | 外部 → backend | RAN sim 推 RSRP/SINR；寫 history + upsert ue_state + 轉發 Kit | 1–10 Hz |
| 1.2 | Ingest | SceneIngestor/create | 外部 → backend | 場景工具灌整份 scene；存 snapshot + upsert gnb_config | 少，手動 |
| 2.1 | Scene | SceneStateReader/read | frontend → backend | 場景摘要（buildings/gnbs/ues 數 + animating）| 1 Hz 輪詢 |
| 2.2 | Scene | SceneLayoutReader/read | frontend → backend | 完整場景（建築/gnb/ue 含座標）| mount 1 次 |
| 2.3 | Scene | SceneController/build | frontend → backend | 叫 Kit 依 scene_config.json 建場景 | 按鈕 |
| 2.4 | Scene | SceneController/clear | frontend → backend | 清空 /World | 按鈕 |
| 2.5 | Scene | AnimationController/start | frontend → backend | 啟動 UE waypoint 動畫 | 按鈕 |
| 2.6 | Scene | AnimationController/stop | frontend → backend | 停止動畫，UE 停在當下 | 按鈕 |
| 3.1 | UE | UEReader/read | frontend → backend | 所有 UE 當下 snapshot（HTTP fallback）| WS 掉時 1 Hz |
| 3.2 | UE | UEController/move | frontend → backend | UE 瞬移到座標（debug）| 按鈕 |
| 3.3 | UE | UEController/trajectory | frontend → backend | 指定 UE 沿 waypoints 跑 | Apply |
| 4.1 | GNB | GNBReader/read | frontend → backend | 讀所有 gNB 設定 | mount / refresh |
| 4.2 | GNB | GNBController/update | frontend → backend | 改 power/active/freq/bw/pos；DB + Kit + dt-ue bridge | 按鈕 |
| 5.1 | Coverage | CoverageReader/read | frontend → backend | 讀 cache coverage map | mount 1 次 |
| 5.2 | Coverage | CoverageRunner/trigger | frontend → backend | 叫 ranp-sim 重算 coverage + 更新 cache | Recompute |
| 6.1 | History | PositionHistoryReader/read | frontend → backend | 某 UE 歷史軌跡 | 需要時 |
| 6.2 | History | SignalHistoryReader/read | frontend → backend | 某 UE RSRP/SINR 時序 | 5 s 輪詢 |
| 7.1 | Platform | PlatformReporter/create | backend → 外部 | Omniver 往外推事件（stub）| 事件觸發 |
| 8.1 | WS | UE/live | server → browser | UE snapshot 即時串流（非 REST） | 500ms push |

---

## 2. Module: Ingest（外部 → backend）

### 2.1 SignalIngestor/create

**URL**：`/api/v0.1/RAN/Ingest/SignalIngestor/create`
**用途**：RAN 模擬器（Sionna / ranp-sim）把算出的 RSRP / SINR 推進來。後端一筆 request 做三件事：寫 `signal_history` 時序表、upsert `ue_state` 最新快照、轉發 Kit `POST /ue/{name}/signal`（寫 USD `ran:*` 屬性 → HUD label 即時更新）。

| Request 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `ts` | ISO 8601 | ❌ | 時戳，預設 server 現在 |
| `signals[]` | array | ✅ | 可批次多筆 |
| `signals[].ue_name` | string | ✅ | 對應 `/World/{ue_name}` |
| `signals[].serving_cell` | string | ✅ | 目前 serving gNB 名稱 |
| `signals[].rsrp_dbm` | float | ✅ | 單位 dBm |
| `signals[].sinr_db` | float | ✅ | 單位 dB |
| `signals[].rsrp_map` | `{gnb: dbm}` | ❌ | 鄰居基地台量測（handover 決策）|

**Request body**
```json
{
  "ts": "2026-04-18T06:30:00Z",
  "signals": [
    {
      "ue_name": "UE_Handover_Path",
      "serving_cell": "gNB_Macro_NW",
      "rsrp_dbm": -78.2, "sinr_db": 12.5,
      "rsrp_map": { "gNB_Macro_NW": -78.2, "gNB_Macro_SE": -92.1 }
    }
  ]
}
```

**Response**
```json
{ "success": true, "message": "OK", "data": { "accepted": 1, "kit_errors": 0 } }
```
`kit_errors` > 0 代表 Kit 離線；DB 還是寫成功。

---

### 2.2 SceneIngestor/create

**URL**：`/api/v0.1/RAN/Ingest/SceneIngestor/create`
**用途**：場景工具把整份場域（buildings + gNBs + UEs）寫進 DB。⚠️ **不會觸發 Kit 重建 viewport**（Kit 是讀 host 上的 `scene_config.json`，兩條路解耦，要另外呼叫 `SceneController/build`）。

| Request 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `scene_id` | string | ✅ | 必須跟 ranp-sim 載入的 id 一致 |
| `buildings[]` | array | ✅ | 每筆 `{name, position[3], size[3], material?}` |
| `gnbs[]` | array | ✅ | `{name, position[3], frequency_ghz, power_dbm, bandwidth_mhz}` |
| `ues[]` | array | ✅ | `{name, position[3], waypoints?, speed_mps?}` |

**Request body**
```json
{
  "scene_id": "umi_3sector_v1",
  "buildings": [{ "name": "Office_NW", "position": [-50,0,50], "size": [30,25,30], "material": "concrete" }],
  "gnbs":      [{ "name": "gNB_Macro_NW", "position": [-90,30,90], "frequency_ghz": 3.5, "power_dbm": 43, "bandwidth_mhz": 100 }],
  "ues":       [{ "name": "UE_1", "position": [0,0,0], "waypoints": [[0,0,0],[50,0,50]], "speed_mps": 2.0 }]
}
```

**Response**
```json
{ "success": true, "message": "stored", "data": { "scene_uuid": "scene_7c3f...", "scene_id": "umi_3sector_v1" } }
```

---

## 3. Module: Scene（場景控制）

所有 Scene endpoint 的 Request body 都是 `{}`，除非下表有標註。

| Endpoint | 用途 | Response.data |
|---|---|---|
| `Scene/SceneStateReader/read` | 摘要（1 Hz 輪詢用）| `{ buildings: 6, gnbs: 3, ues: 5, animating: true }` |
| `Scene/SceneLayoutReader/read` | 完整靜態場景 | `{ buildings: [...], gnbs: [...], ues: [...], ground: {...} }` |
| `Scene/SceneController/build` | 依 scene_config.json 建 USD（非同步）| `{ action: "build" }` |
| `Scene/SceneController/clear` | 清空 /World | `{ action: "clear" }` |
| `Scene/AnimationController/start` | 啟動 UE waypoint 動畫 | `{ action: "start" }` |
| `Scene/AnimationController/stop` | 停止動畫 | `{ action: "stop" }` |

**SceneLayoutReader response 範例**：
```json
{ "success": true, "message": "OK", "data": {
  "buildings": [{ "name": "Office_NW", "position": {"x":-50,"y":0,"z":50}, "size": {"x":30,"y":25,"z":30}, "material": "concrete" }],
  "gnbs":      [{ "name": "gNB_Macro_NW", "position": {"x":-90,"y":30,"z":90}, "freq_mhz": 3500, "power_dbm": 43, "bw_hz": 100000000, "active": true }],
  "ues":       [{ "name": "UE_1", "position": {"x":0,"y":0,"z":0}, "serving_cell": "gNB_Macro_NW", "rsrp_dbm": -78.0, "sinr_db": 12.0 }],
  "ground":    { "size": [250,250], "position": [0,0,0] }
}}
```

**注意**：build / clear / start / stop 是 **非同步**，Response 200 只代表指令送達 Kit command queue，實際執行要再問 SceneStateReader/read 確認。

---

## 4. Module: UE（使用者設備）

### 4.1 UEReader/read

**URL**：`/api/v0.1/RAN/UE/UEReader/read` — Request body = `{}`
**用途**：所有 UE 當下 snapshot（HTTP fallback；即時請走 WebSocket）。

**Response.data** = UE 物件陣列：
```json
[
  { "name": "UE_Handover_Path", "position": {"x":22,"y":0,"z":-22}, "serving_cell": "gNB_Macro_NW", "rsrp_dbm": -78, "sinr_db": 12 },
  { "name": "UE_NLOS_Shadow",   "position": {"x":-30,"y":0,"z":15}, "serving_cell": null, "rsrp_dbm": null, "sinr_db": null }
]
```
訊號欄位是 `null` = 該 UE 還沒被 ingest 過訊號。

---

### 4.2 UEController/move（瞬移）

**URL**：`/api/v0.1/RAN/UE/UEController/move`

| Request 欄位 | 型別 | 必填 |
|---|---|---|
| `name` | string | ✅ |
| `x`, `y`, `z` | float | ✅ |

```json
{ "name": "UE_Handover_Path", "x": 10.0, "y": 0.0, "z": 20.0 }
```

**Response.data** = `{ name, x, y, z }`。只改 position，不改動畫；下一幀動畫會把它拉回去（除非先 stop animation）。

---

### 4.3 UEController/trajectory（指定軌跡）

**URL**：`/api/v0.1/RAN/UE/UEController/trajectory`

| Request 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `name` | string | ✅ | UE 名 |
| `waypoints` | `[[x,y,z], ...]` | ✅ | **至少 2 點** |
| `speed_mps` | float | ✅ | 移動速度 |
| `loop` | bool | ❌ | `true` ping-pong；`false` 走完停；預設 true |

```json
{ "name": "UE_Handover_Path", "waypoints": [[0,0,0],[20,0,-20],[0,0,-40]], "speed_mps": 3.0, "loop": true }
```

**Response.data** = `{ name, waypoints_count }`。Kit 內部把舊 waypoints 原地覆寫，不需要先 stop。

---

## 5. Module: GNB

### 5.1 GNBReader/read

**URL**：`/api/v0.1/RAN/GNB/GNBReader/read` — Request body = `{}`
**Response.data** = gNB 物件陣列：
```json
[{ "name": "gNB_Macro_NW", "position": {"x":-90,"y":30,"z":90}, "freq_mhz": 3500, "power_dbm": 43, "bw_hz": 1e8, "active": true }]
```

---

### 5.2 GNBController/update

**URL**：`/api/v0.1/RAN/GNB/GNBController/update`
**用途**：改 gNB 參數或位置。後端會做 **3 階段 fan-out**：
1. 寫 `gnb_config` DB（canonical 值）
2. 推 Kit `POST /gnb/{name}/update` → viewport + HUD label 更新
3. 推 dt-ueinference `GnbUpdater/push` → ranp-sim `push_scene(ran_only)` → Sionna 重建

| Request 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `name` | string | ✅ | gNB 名 |
| `power_dbm` | float | ❌ | 發射功率 |
| `active` | bool | ❌ | 開關 |
| `frequency_ghz` | float | ❌ | 載波頻率 |
| `bandwidth_mhz` | float | ❌ | 頻寬 |
| `position` | `[x,y,z]` | ❌ | 移動位置 |

```json
{ "name": "gNB_Macro_NW", "power_dbm": 40.0, "bandwidth_mhz": 80.0 }
```

**Response.data**：
```json
{ "name": "gNB_Macro_NW", "applied": ["power_dbm","bandwidth_mhz"], "bridge": "pushed" }
```
若 Kit 離線 → `kit_error: "..."`；若 bridge 失敗 → `bridge_error: "..."`（DB 還是會寫成功）。

---

## 6. Module: Coverage

### 6.1 CoverageReader/read

**URL**：`/api/v0.1/RAN/Coverage/CoverageReader/read`
**用途**：讀 cache 的覆蓋地圖（Trajectory 頁 heatmap / serving 層在用）。cache miss → 404，要先呼 `CoverageRunner/trigger`。

```json
{ "scene_id": "umi_3sector_v1" }
```

**Response.data**：
```json
{
  "scene_id": "umi_3sector_v1", "ts": "2026-04-20T10:15:30Z", "compute_ms": 1247,
  "grid": { "x_range":[-125,125], "x_step":5, "z_range":[-125,125], "z_step":5, "n_rows":50, "n_cols":50, "sample_height_m":1.5 },
  "gnbs": [{ "gnb_name": "gNB_Macro_NW",
             "rsrp_dbm": [[-120,-115,null,...], ...],
             "sinr_db":  [[12,null,null,...], ...] }]
}
```
- `rsrp_dbm[row][col] == null` → 格點在 grid 外
- `sinr_db[row][col] == null` → 該格不是這顆 gNB 的 serving cell

---

### 6.2 CoverageRunner/trigger

**URL**：`/api/v0.1/RAN/Coverage/CoverageRunner/trigger`
**用途**：叫 ranp-sim 重算 coverage，結果 upsert 進 `coverage_map` 表；下次 `CoverageReader/read` 直接讀到新值。

| Request 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `scene_id` | string | ✅ | |
| `grid.x_range` / `z_range` | `[min,max]` | ❌ | 預設 ±125 |
| `grid.x_step` / `z_step` | float | ❌ | 預設 5 m |
| `include_sinr` | bool | ❌ | 預設 true |

```json
{ "scene_id": "umi_3sector_v1", "grid": { "x_range":[-125,125], "x_step":5, "z_range":[-125,125], "z_step":5 }, "include_sinr": true }
```

**Response.data** = `{ scene_id, cached: true }`。cached=true 代表 DB 寫成功。

---

## 7. Module: History

兩支 endpoint 同樣的 Request 格式：

| Request 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `ue_name` | string | ✅ | |
| `since` | 相對 `-5m`/`-15m`/`-30m`/`-1h` 或 ISO 8601 | ❌ | 預設 -15m |

### 7.1 PositionHistoryReader/read

**URL**：`/api/v0.1/RAN/History/PositionHistoryReader/read`
**用途**：某 UE 一段時間的 (x,y,z) 軌跡。

**Response.data** = 按 `ts` 升冪的點陣列：
```json
[
  { "ts": "2026-04-20T10:00:00Z", "x": 0, "y": 0, "z": 0 },
  { "ts": "2026-04-20T10:00:01Z", "x": 2, "y": 0, "z": -2 }
]
```

### 7.2 SignalHistoryReader/read

**URL**：`/api/v0.1/RAN/History/SignalHistoryReader/read`
**用途**：Signal History 頁 RSRP/SINR 時序圖的資料源（5 s 輪詢）。

**Response.data** = 按 `ts` 升冪：
```json
[{ "ts": "2026-04-20T10:00:00Z", "serving_cell": "gNB_Macro_NW", "rsrp_dbm": -78.2, "sinr_db": 12.5,
   "rsrp_map": { "gNB_Macro_NW": -78.2, "gNB_Macro_SE": -92.1 } }]
```
`rsrp_map` 只有 ingest 時帶入才有。

---

## 8. Module: Platform（方向相反）

### 8.1 PlatformReporter/create

**URL**：`/api/v0.1/RAN/Platform/PlatformReporter/create`
**用途**：**Omniver 主動往外推事件**（UE 座標 / 告警 / handover）。外部平台還沒接時先落 `platform_event` 表 + log，之後換 real forwarder。

| Request 欄位 | 型別 | 必填 |
|---|---|---|
| `event` | string | ✅ (例 `ue_positions`, `handover`) |
| `payload` | object | ✅ 事件內容 |

```json
{ "event": "ue_positions", "payload": { "ts":"2026-04-18T06:30:00Z", "ues":[{"name":"UE_1","x":0,"y":0,"z":0}] } }
```

**Response.data** = `{ event_uuid: "evt_..." }`（可拿來查 `platform_event` 表）。

---

## 9. WebSocket（即時串流）

### 9.1 UE Live Stream

| 項目 | 值 |
|---|---|
| URL | `ws://<host>:8001/api/v0.1/RAN/UE/live` |
| 方向 | server → browser（client send 會被忽略）|
| 連上第一訊息 | `{ "type": "hello", "group": "ue_live" }` |
| 後續頻率 | 500 ms per `ue_update` |
| 資料源 | Kit :8081 → backend Channels group → 訂閱 clients |
| 掉線行為 | backend 會推 `{ ues: [] }`，Kit 回來自動補；backend 有指數 backoff 重連 |

**`ue_update` 格式**：
```json
{ "type": "ue_update", "ts": "2026-04-18T06:30:00.500Z",
  "ues": [{ "name":"UE_1", "position":{"x":0,"y":0,"z":0},
            "serving_cell":"gNB_Macro_NW", "rsrp_dbm":-78.0, "sinr_db":12.0 }] }
```

---

## 10. 錯誤回應

| HTTP | 意義 | message 範例 |
|---|---|---|
| **400** | JSON 壞 / 欄位缺 / 型別錯 | `"Validation failed"` + `errors: {field: [msgs]}` |
| **404** | 資源不存在（UE/gNB 名不對、Coverage 沒算過）| `"gNB 'X' not found"` / `"No coverage for X; call CoverageRunner/trigger first"` |
| **422** | `since` 格式無效 | `"Invalid time format"` |
| **502** | Kit 離線 / ranp-sim 不在 | `"Kit unreachable"` + `errors.detail` |

---

## 11. 資料型別速查

**UE 物件**
```json
{ "name": "UE_X", "position": {"x":0,"y":0,"z":0},
  "serving_cell": "gNB_X" | null, "rsrp_dbm": float|null, "sinr_db": float|null }
```

**gNB 物件**
```json
{ "name": "gNB_X", "position": {"x":0,"y":0,"z":0},
  "freq_mhz": 3500, "power_dbm": 43, "bw_hz": 1e8, "active": true }
```

**Building 物件**
```json
{ "name": "Office_X", "position": {"x":0,"y":0,"z":0},
  "size": {"x":30,"y":25,"z":30}, "material": "concrete" }
```

---

## 12. 相關文件

| 文件 | 內容 |
|---|---|
| `docs/api.md` | 完整 API 清單（含讀 / 控制類）|
| `docs/platform_inputs.md` | 啟動平台要的所有輸入（硬體 / env / 場景）|
| `docs/kit_internals_101.md` | Kit extension 內部 + USD attr |
| `ranp-sim/docs/INPUT_SPEC.md` | ranp-sim 輸入規格 |
| `backend_rule.md` | 後端鐵則（全 POST / URL 格式 / serializer 等）|
