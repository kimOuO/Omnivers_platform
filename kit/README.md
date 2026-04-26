# 🎮 Omniverse Kit 容器

完整容器化的 NVIDIA Omniverse Kit 伺服器，支援 GPU 加速和虛擬顯示。

---

## 概述

Kit 容器提供：

- **3D 場景渲染**：基於 Vulkan 和 RTX 光線追蹤
- **HTTP API**：Port 8080 提供場景控制和狀態查詢
- **WebSocket 支援**：Port 8081 用於實時快照推送
- **虛擬顯示**：Port 5900 (VNC) + Port 6080 (noVNC Web)
- **GPU 加速**：自動檢測和使用 NVIDIA GPU

---

## 啟動方式

### 透過 Docker Compose（推薦）

```bash
# 啟動所有服務（包括 Kit）
docker compose up -d

# 單獨啟動或重啟 Kit
docker compose up -d kit
docker compose restart kit
```

### 查看 Kit 日誌

```bash
# 實時查看日誌
docker compose logs -f kit

# 查看最後 100 行
docker compose logs --tail 100 kit

# 儲存日誌到檔案
docker compose logs kit > kit.log
```

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| **Dockerfile** | Kit 容器定義（系統依賴、Omniverse Kit 安裝、入口點） |
| **entrypoint.sh** | 容器啟動指令（Xvfb、VNC、websockify、Kit 初始化） |
| **run_kit.py** | Python EULA 自動接受包裝器 |
| **ran_server.kit** | Kit 應用配置檔（擴展載入、設定項） |

---

## 容器配置

### docker-compose.yml 中的 Kit 設定

```yaml
kit:
  build:
    context: .
    dockerfile: kit/Dockerfile
  container_name: omniver_kit
  runtime: nvidia                      # 啟用 GPU
  environment:
    NVIDIA_VISIBLE_DEVICES: all       # 所有 GPU 可見
    NVIDIA_DRIVER_CAPABILITIES: graphics,compute,utility,display
  ports:
    - "8080:8080"   # Kit HTTP API
    - "8081:8081"   # Kit WebSocket
    - "5900:5900"   # VNC 伺服器
    - "6080:6080"   # noVNC Web
  ipc: host         # 提高顯示性能
  restart: unless-stopped
```

---

## 訪問 Kit

### HTTP API (Port 8080)

```bash
# 列出可用的 API 端點
curl http://localhost:8080/

# 查詢場景狀態
curl http://localhost:8080/scene/status

# 構建場景
curl -X POST http://localhost:8080/scene/build \
  -H "Content-Type: application/json" \
  -d '{"name":"test_scene"}'
```

### VNC Web (Port 6080)

```
http://localhost:6080/vnc.html
```

**功能**：
- 實時查看 3D 場景
- 滑鼠和鍵盤控制
- 無需額外軟體

### 原生 VNC (Port 5900)

```
vnc://localhost:5900
```

使用 VNC 客戶端（如 TightVNC、RealVNC）連接。

---

## 技術細節

### Dockerfile 架構

```dockerfile
FROM nvidia/cuda:12.6.0-base-ubuntu22.04  # GPU 支援基礎
  ├─ 安裝系統依賴（Python、X11、VNC）
  ├─ 安裝 omniverse-kit 106.0.3（pip）
  ├─ 複製配置和擴展
  ├─ 複製 entrypoint.sh
  └─ 暴露連接埠 (8080, 8081, 5900, 6080)
```

### entrypoint.sh 流程

```
1. 啟動 Xvfb (虛擬顯示 :99)
2. 配置 xrandr (1920x1080 @ 60Hz)
3. 啟動 x11vnc (VNC 伺服器)
4. 啟動 websockify (noVNC 代理)
5. 啟動 Kit (自動接受 EULA)
6. 監視所有程序
```

### Omniverse Kit 版本

- **版本**：106.0.3.138428
- **來源**：PyPI (omniverse-kit 套件)
- **Python**：3.10
- **渲染**：Vulkan (GPU 加速)

---

## 問題排除

### Kit 不回應 API

```bash
# 檢查容器狀態
docker compose ps kit

# 查看詳細日誌
docker compose logs kit | grep -i error

# 重啟 Kit
docker compose restart kit

# 進入容器調試
docker exec -it omniver_kit bash
```

### VNC 無法連接

```bash
# 檢查 VNC 伺服器狀態
docker exec omniver_kit ps aux | grep vnc

# 檢查連接埠
docker exec omniver_kit netstat -tulpn | grep -E "5900|6080"

# 重啟 Kit
docker compose restart kit
```

### GPU 未被識別

```bash
# 測試主機 GPU
nvidia-smi

# 測試容器 GPU 訪問
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi

# 檢查 Kit 容器的 GPU
docker exec omniver_kit nvidia-smi
```

### 磁碟空間不足

```bash
# 檢查容器檔案系統大小
docker exec omniver_kit du -sh /root/.local/share/ov/data/

# 清理快取
docker exec omniver_kit rm -rf /root/.local/share/ov/data/exts/*
```

---

## 性能最佳化

### GPU 監控

```bash
# 實時 GPU 使用
docker exec omniver_kit watch nvidia-smi

# 檢查 CUDA 可用性
docker exec omniver_kit nvidia-smi --query-gpu=name,memory.total
```

### 記憶體調整

增加 Kit 記憶體限制（docker-compose.yml）：

```yaml
kit:
  deploy:
    resources:
      limits:
        memory: 16G  # 根據實際系統調整
```

### 顯示性能

- `ipc: host` 已啟用（提高 IPC 性能）
- Vulkan 驅動已優化
- 虛擬顯示配置為 60Hz

---

## 維護

### 備份配置

```bash
# 備份 Kit 配置
docker cp omniver_kit:/app/kit/ran_server.kit ./backup/ran_server.kit.backup

# 備份場景配置
docker cp omniver_kit:/app/scene_config.json ./backup/scene_config.json.backup
```

### 清理快取

```bash
# 清理 Kit 擴展快取
docker exec omniver_kit rm -rf /root/.local/share/ov/data/exts/*

# 清理 GPU 快取
docker exec omniver_kit rm -rf /root/.local/share/ov/data/Kit/ran_server/*/
```

### 重新構建

```bash
# 完全重建（不使用快取）
docker compose build --no-cache kit

# 重新啟動
docker compose up -d kit
```

---

## 相關資源

- **主文檔**：../README.md
- **Docker 操作**：../DOCKER_QUICKSTART.md
- **場景配置**：../SCENE_CONFIG_GUIDE.md
- **Kit 擴展**：../extensions/README.md
- **API 文檔**：../docs/ingest_api.md

---

## 授權

Omniverse Kit 基於 NVIDIA Omniverse Kit SDK。詳見 ../README.md 的授權部分。
