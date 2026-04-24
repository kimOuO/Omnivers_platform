# Kit Extensions

已從 `kit-app-template/source/extensions/` 搬出的 Kit Python extensions。
由 `../kit/ran_server.kit` 的 `[settings.app.exts] folders.'++'` 載入。

## 現有

### `mitlab.ran.scene.builder/`
造景 + UE 動畫。對應 config 透過 env var `RAN_SCENE_CONFIG` 指定
（預設 `~/omniverse/scene_config.json`）。S1 新增 `update_trajectory(name, waypoints, speed_mps, loop)` 公開方法。

### `mitlab.ran.api/`  (v0.2.0)
Port 8080 HTTP API，瘦身後只做 stage CRUD + 命令佇列。
不再依賴 signal extension。

新增 endpoints：
- `POST /ue/{name}/trajectory` body: `{waypoints, speed_mps, loop}` → 呼叫 builder.update_trajectory
- `POST /ue/{name}/signal`     body: `{serving_cell, rsrp_dbm, sinr_db, rsrp_map}` → 寫入 USD custom attrs

刪掉的 endpoints：
- `GET /dashboard` (Dashboard 已搬到 Next.js 前端)
- `GET /ue/{name}/signal` (讀訊號改由 backend DB 查)

### `mitlab.ran.labels/`  (S5 新增 ✅)
用 `omni.ui.scene` 在每個 UE 頭上畫 billboard，文字來自 `ran:*` custom attrs。
- 離 UE 頭頂 `LABEL_OFFSET_Y = 6.0` m
- `LookAt.CAMERA` 永遠面對鏡頭
- `scale_to=SCREEN` 保持像素大小
- 10 Hz 重繪（`UPDATE_HZ`）
- RSRP > -80 綠 / > -100 橘 / 更低 紅

## 已刪除

### `mitlab.ran.signal/`
FSPL 解析式訊號計算。S1 廢除 —— 訊號改由外部模擬 RAN 透過
`POST /api/v0.1/RAN/Ingest/SignalIngestor/create` → Django backend → Kit
`POST /ue/{name}/signal` 的流程餵入。
