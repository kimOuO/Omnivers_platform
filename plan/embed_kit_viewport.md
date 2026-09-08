# 計劃：把 Omniverse（noVNC）畫面嵌到 Scene Layout 旁邊

日期：2026-09-08

## 0. 現況（已查證）

- Kit 容器 `kit/entrypoint.sh:45` 跑 `websockify --web /usr/share/novnc 6080 localhost:5900`，
  `docker-compose.yml:104` 對外開 **6080**。實測 `GET /vnc.html` 回 **200**。
- noVNC 檔案齊全：`vnc.html`（完整 UI，有側邊工具列）、**`vnc_lite.html`**（極簡，無工具列）。
- Dashboard **已經有這個設定**，只是沒人用：
  - `app/layout.tsx:22` → `vncUrl: process.env.VNC_URL || 'http://localhost:6080/vnc.html'`
  - `config/index.ts:55` → `export const VNC_URL = ...`
  - `Physics_sim/docker-compose.yml` 也有 `NEXT_PUBLIC_VNC_URL`
- Xvfb 解析度 **1920×1080**（`Xvfb :99 ... -screen 0 1920x1080x24`）。
- x11vnc 參數：`-noshm -noxdamage -noscr -nowf -noxfixes -ncache 0` —— 這組是「相容優先」，
  等於關掉所有增量更新最佳化，**每次都推整張畫面**。

---

## 1. 可行性：可以，而且是 iframe 就好

noVNC 是純前端的 JS 客戶端，透過 WebSocket 連 websockify。嵌進 Next.js 只要一個
`<iframe>`，**不需要 CORS**（iframe 不是 XHR），也不需要同源。

`vnc.html` 支援 URL 查詢參數，關鍵的幾個：

| 參數 | 用途 |
|---|---|
| `autoconnect=true` | 載入即連線，不用按 Connect |
| `resize=scale` | 把 1920×1080 縮放塞進 iframe 尺寸（不是裁切） |
| `view_only=1` | 唯讀，滑鼠鍵盤不會傳進 Kit |
| `quality=0..9` / `compression=0..9` | 畫質 vs 頻寬 |
| `reconnect=true` | 斷線自動重連 |

`vnc_lite.html` 沒有側邊工具列，畫面更乾淨，但不支援上面全部參數。
**建議用 `vnc.html` + 參數**，工具列可以用 CSS 蓋掉。

---

## 2. 三個要面對的問題

### 2.1 畫面裡有整個 Kit UI，不只是 viewport

VNC 送的是整個 X display：Kit 的選單列、工具列、以及那兩個浮動的
「RAN Scene Builder / RAN API」面板（先前排查時就是它們擋住走廊）。
嵌到只有幾百像素寬的側欄時，viewport 實際可見面積會很小。

三種處理方式：

1. **CSS 裁切**（純前端）：把 iframe 放大後用 `overflow:hidden` + `transform: translate()`
   只露出 viewport 那塊。缺點是 Kit 視窗佈局一變就要重調偏移量。
2. **關掉 Kit 的浮動面板**（後端）：`mitlab.ran.api` 已經有
   `_hide_dock_panels()`（extension.py:412）在啟動時關掉 Stage/Property/Console 等。
   把自家那兩個面板也一起收起來，或加一個 API 開關。
3. **兩者都做**：面板收乾淨 + CSS 只裁掉頂端選單列。**建議這個**。

### 2.2 頻寬與 CPU

x11vnc 現在是 `-noshm -noxdamage -noscr`，等於**全畫面重推**。1920×1080 的
RTX 視窗持續更新（UE 在走廊裡走動 = 畫面一直變），VNC 會吃掉可觀的 CPU 與頻寬。

可做的（由輕到重）：
- iframe 加 `quality=6&compression=6`（noVNC 端調 JPEG 品質）
- 只在使用者「展開」VNC 面板時才掛載 iframe（收合就 unmount，連線斷開）
- 真的要省：把 Xvfb 降到 1280×720，並拿掉 x11vnc 的 `-noxdamage`
  （這是改 `kit/entrypoint.sh`，會影響所有使用者，需要你點頭）

### 2.3 兩個視圖不會同步

左邊 R3F 畫布與右邊 Kit viewport 是各自獨立的相機。點左邊的 UE，右邊不會跟著看過去。

要同步得在 Kit extension 新增一個「設定 viewport 相機」的 API
（`POST /viewport/look_at {target, distance}`），前端選取物件時呼叫它。
**這是額外工作，建議先不做**，等基本嵌入用起來覺得需要再說。

---

## 3. 實作計劃

### 步驟 1 — `KitViewport.tsx`（前端，主要工作）
- 一個可收合的面板，內含 `<iframe src={VNC_URL}?autoconnect=true&resize=scale&...>`
- **收合時 unmount iframe**，不要只是 `display:none` —— VNC 連線會一直吃資源
- 工具列：連線狀態、唯讀/可操作切換（`view_only`）、重新連線、開新視窗
- 預設 **唯讀**：避免使用者在嵌入的小畫面裡誤拖 Kit 的物件

### 步驟 2 — editor 頁改成左右並排
`app/editor/page.tsx:786` 的 Scene Layout 區塊改成 grid：
左邊現有畫布（2D/3D 切換），右邊 `KitViewport`。窄螢幕時上下堆疊。

### 步驟 3 — 收乾淨 Kit 的浮動面板
`mitlab.ran.api` 的 `_hide_dock_panels()` 把 `"RAN Scene Builder"`、`"RAN API"`
也加進去，或加一個 `POST /ui/panels {visible}` 讓前端切換。
（那兩個面板是開發時方便用的，正式看畫面時反而擋路。）

### 步驟 4（選做）— 相機同步
Kit extension 加 `POST /viewport/focus {prim_path}` 或 `{x,y,z,distance}`，
前端點選物件時一併呼叫。等前三步用順了再評估。

---

## 4. 建議與風險

**先做步驟 1 + 2**，那是純前端、可逆、不影響任何既有功能。
步驟 3 動到 Kit extension，要重啟 Kit（約 60–75 秒），建議跟其他 Kit 改動一起做。

最大的風險是**效能**：如果 iframe 一掛上去整頁變卡，多半是 VNC 全畫面重推造成的，
那就走 2.2 的第三條（降 Xvfb 解析度 / 開 xdamage），但那要改 entrypoint 並重啟 Kit。
