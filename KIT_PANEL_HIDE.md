# Kit 側邊面板隱藏 — 原因與解法

## 問題現象

在 noVNC（port 6080）開啟 Omniverse Kit 看 RAN 數位孿生時，3D viewport 被 Kit 預設的 dock panel 擠在中間一小塊：

| 面板 | 位置 | 來源 extension |
|------|------|----------------|
| Stage | 右上 | `omni.kit.window.stage` |
| Render Settings | 右上（與 Stage 同 dock） | `omni.rtx.window.settings` |
| Property | 右下 | `omni.kit.window.property` |
| Console | 左下 | `omni.kit.window.console` |
| Content | 左下（與 Console 同 dock） | `omni.kit.window.content_browser` |

需求：把這五個面板隱藏，3D viewport 佔滿畫面，但保留頂部 menu bar、左側 toolbar、底部 status bar，以及自家擴充的 RAN Scene Builder / RAN API 小視窗（保留手動 Build/Clear 入口）。

---

## 為什麼一般做法都失敗

### ❌ 方法 1：CLI flag `--/exts/<name>/show=false`

`kit/entrypoint.sh` 原本嘗試傳：

```
--/exts/omni.kit.window.stage/show=false
--/exts/omni.kit.window.property/show=false
--/exts/omni.kit.window.content_browser/show=false
```

**失敗原因**：`/exts/<name>/show` 根本**不是 Kit 真正的 setting path**。Kit 沒有這個慣例，這些 flag 寫了等於沒寫。

### ❌ 方法 2：`app.docks.disabled = true`

NVIDIA 自己的單 viewport sample `omni.app.viewport.kit:27` 用這行，看起來很官方。

**失敗原因**：那個 sample 之所以能用，是因為它**根本沒在 `[dependencies]` 載入**那五個 window extension。我們的 `ran_server.kit` 是基於 `kit_base_editor` template，必須載入這些 ext（被 `omni.kit.developer.bundle` / `omni.kit.property.bundle` transitively 拉進來）。Window 已經被建立後，`docks.disabled` 並不會把它們隱藏 — 只是讓 dock 系統「邏輯上停用」，UI 視覺上還是在。

### ❌ 方法 3：在 `[dependencies]` 寫 `{ enabled = false }`

```toml
"omni.kit.window.stage" = { enabled = false }
"omni.kit.window.property" = { enabled = false }
...
```

**失敗原因**：在 Kit 的依賴解析裡，**bundle 的 transitive `required` 大於我們的 `enabled = false` hint**。實測 log 顯示 `[ext: omni.kit.window.stage-2.6.1] startup` 仍照樣執行 — bundle 把它們又拉回來啟動了。

---

## 根本原因

| 層次 | 真相 |
|------|------|
| **Kit 110.0.0 的設計** | Window 由 ext 在 startup 時主動建立，預設 `visible = True`。沒有「全域 ext 黑名單」這種設定可以從外部關掉一個 ext 的 window 創建 |
| **Bundle 的問題** | `omni.kit.developer.bundle` 與 `omni.kit.property.bundle` 強制 require 那五個 window ext，個別 disable 都被 override |
| **能直接動的層次** | 只剩 **runtime API**：window 被建立**之後**，主動把 `.visible` 設成 False |

---

## ✅ 最終解法

在自家 ext `mitlab.ran.api` 的 `on_startup` 裡跑一個 async coroutine，**等 window 被建立後**，用 `omni.ui.Workspace.get_window(name)` 抓到它，把 `.visible` 設成 False。為了處理 lazy-create 的 window，polling 20 個 update tick（約 1 秒）多次 hide。

### 程式碼位置

`extensions/mitlab.ran.api/mitlab/ran/api/extension.py:381` 在 `on_startup` 末段加：

```python
self._panel_hide_task = omni.kit.async_engine.run_coroutine(self._hide_dock_panels())
```

對應的 coroutine（同檔 `:385`）：

```python
async def _hide_dock_panels(self):
    panel_names = ["Stage", "Property", "Console", "Content", "Render Settings", "Layer"]
    app = omni.kit.app.get_app()
    for _ in range(20):
        await app.next_update_async()
        for n in panel_names:
            try:
                win = ui.Workspace.get_window(n)
                if win is not None and win.visible:
                    win.visible = False
            except Exception as e:
                print(f"[mitlab.ran.api] hide panel '{n}': {e}")
    print(f"[mitlab.ran.api] dock panels hidden: {panel_names}")
```

### 為什麼用 polling 而不是一次

Kit 的 dock layout 在啟動後幾百毫秒內仍會繼續變動（lazy-create、autosave layout 還原等）。一次性 hide 可能會被後續 layout restore 蓋回來。20 ticks ≈ 1 秒，足以涵蓋啟動期所有 window 出現的時機，又不會永久占用 update loop。

---

## 驗證

### 1. 看 Kit 內部 log（不要看 `docker compose logs`）

`docker compose logs kit` 會把長 stdout 截斷，**找不到 `[mitlab.ran.api]` 的 print 訊息**。Kit 有自己的 log file：

```bash
docker exec omniver_kit bash -c \
  "grep -E 'dock panels|hide panel' /root/.nvidia-omniverse/logs/Kit/ran_server/0.2/kit_*.log"
```

預期看到：

```
[py stdout]: [mitlab.ran.api] dock panels hidden: ['Stage', 'Property', 'Console', 'Content', 'Render Settings', 'Layer']
```

如有 `hide panel 'X': <error>` 表示某個 window 名稱拼錯或在不同版本裡叫別的名字。

### 2. HTTP API

```bash
curl -sS http://localhost:8080/scene/status
```

回 JSON 即代表 `mitlab.ran.api` extension 正常啟動（panel-hide 邏輯在它裡面）。

### 3. 視覺驗證

瀏覽器開 `http://<host>:6080/vnc.html` 重整：
- ✅ Stage / Property / Console / Content / Render Settings 不見
- ✅ 中間 3D viewport 變大
- ✅ 頂部 menu bar、左 toolbar、底 status bar、自家 RAN Scene Builder / RAN API 視窗仍在

---

## 之後新增 panel 的處理

如果某天 Kit 升級後又冒出新的 dock panel（例如某個新版 ext 加了 "Outliner"），只要把那個 panel 名稱加到 `panel_names` list 就好。**不必動 `.kit` 檔案，不必 rebuild image** — 因為 `extensions/` 是 volume mount，只要重啟 kit 容器即可：

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform
docker compose restart kit
```

## 改動檔案清單

| 檔案 | 改動 |
|------|------|
| `extensions/mitlab.ran.api/mitlab/ran/api/extension.py` | 加 `_hide_dock_panels()` coroutine 與 `on_startup` 啟動該 task |
| `kit/ran_server.kit` | 加 `app.docks.disabled = true` / `app.viewport.defaults.noTitleBar = true` / `persistent.app.viewport.noPadding = true`（這三個對隱藏沒幫助但對 viewport 邊到邊有幫助，留著） |
| `kit/entrypoint.sh` | 移除無效的 `--/exts/omni.kit.window.*/show=false` CLI flag |

## Rollback

只要把 `mitlab.ran.api/extension.py` 裡 `self._panel_hide_task = ...` 那行與整個 `_hide_dock_panels` 方法刪掉，重啟 kit 容器，五個 panel 會立刻回來。資料庫、scene_config、USD stage 都不受影響。
