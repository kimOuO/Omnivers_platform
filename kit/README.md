# Kit Render Server

Long-running Omniverse Kit process. 不走 `kit-app-template` 的 `repo.sh build`，
用 pip 裝的 `omniverse-kit` 直接啟動一個自訂 `.kit` 檔。

## 檔案

- `ran_server.kit` — Kit App 設定（依賴 + 版本鎖 + settings）
- `run.sh` — 啟動腳本

## 前置條件

1. `~/omniverse-env/` 有裝 `omniverse-kit 110.0.0.276876`
   ```bash
   source ~/omniverse-env/bin/activate
   pip install omniverse-kit --extra-index-url https://pypi.nvidia.com
   ```
2. `kit-app-template/_build/linux-x86_64/release/extscache/` 必須存在
   （本檔案引用為 extscache 來源；若不存在，先在 `kit-app-template` 跑一次
   `./repo.sh build` 即可）
3. `scene_config.json` 位於 `/home/mitlab/Omniverse/Omniverse/scene_config.json`
   （可用 env var `RAN_SCENE_CONFIG` 指向其他位置）
4. DISPLAY 已設定（本地 X 或 VNC）

## 啟動

```bash
./run.sh

# 想指定其他場景設定檔：
RAN_SCENE_CONFIG=/path/to/other.json ./run.sh
```

首次啟動可能需要接受 EULA（終端機會出現 `Do you accept the EULA? (Yes/No):`，
回答 `Yes` 即可，之後會自動記錄）。

## 驗證

啟動後：
- VNC/X 會看到 Kit 視窗，標題 `RAN Omniverse Server`
- 右側有 `RAN Scene Builder` 和 `RAN API` 兩個面板
- `curl http://localhost:8080/` 回 API endpoint 列表

## 已知技術債

- extscache 仍依賴 `kit-app-template/_build/...`（symlink-style）。
  未來若要完全斷開 `kit-app-template`，需要自己準備一份 extscache
  （例如 `repo precache_exts` 或 pin 特定版本到 venv）。
