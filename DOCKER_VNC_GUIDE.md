# 🐳 Docker + Xvfb + VNC + noVNC 指南

完整的 Docker 容器化 Omniverse Kit 環境，包含虛擬顯示和遠程桌面訪問。

---

## 📋 檔案說明

| 檔案 | 用途 |
|------|------|
| `Dockerfile.kit-vnc` | Docker 鏡像定義（包含 Xvfb、x11vnc、noVNC） |
| `docker-compose.kit-vnc.yml` | Docker Compose 配置（完整堆棧） |
| `kit-vnc-startup.sh` | Kit 啟動腳本（在容器內執行） |

---

## 🚀 快速啟動

### 前置條件

```bash
✓ Docker 已安裝
✓ Docker Compose 已安裝
✓ NVIDIA GPU + nvidia-docker （用於 GPU 支持）
✓ kit/ 目錄存在
✓ extensions/ 目錄存在
✓ scene_config.json 存在
```

### 啟動完整堆棧

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform

# 啟動所有容器（Kit + PostgreSQL + Django + Next.js）
docker-compose -f docker-compose.kit-vnc.yml up -d

# 查看日誌
docker-compose -f docker-compose.kit-vnc.yml logs -f kit-vnc
```

### 只啟動 Kit VNC

```bash
# 僅啟動 Kit 容器
docker-compose -f docker-compose.kit-vnc.yml up -d kit-vnc
```

---

## 🖥️ 訪問遠程桌面

### 方式 1️⃣：Web 瀏覽器（推薦）

```
http://localhost:6080/vnc.html
```

**優點：**
- ✓ 無需安裝 VNC 客戶端
- ✓ 跨平台（Windows、Mac、Linux）
- ✓ 易於共享

### 方式 2️⃣：VNC 客戶端

使用任何 VNC 客戶端（如 TightVNC、RealVNC 等）：

```
localhost:5900
```

**客戶端推薦：**
- **Windows：** TightVNC Viewer, RealVNC
- **Mac：** VNC Viewer, Apple Remote Desktop
- **Linux：** vncviewer, Remmina

---

## 📱 連接步驟

### 通過 noVNC Web

1. 打開瀏覽器
2. 訪問 `http://localhost:6080/vnc.html`
3. 點擊「Connect」
4. 查看 Omniverse Kit 3D 窗口

### 通過 VNC 客戶端

1. 打開 VNC 客戶端
2. 連接到 `localhost:5900`
3. （無需密碼）

---

## 🔧 配置參數

### 環境變數

在 `docker-compose.kit-vnc.yml` 中修改：

```yaml
environment:
  DISPLAY: ":99"              # X display 號
  DISPLAY_SIZE: "2560x1440"   # 解析度
  DISPLAY_DEPTH: "24"         # 色深（24-bit）
  VNC_PORT: "5900"            # VNC port
  VNC_WEB_PORT: "6080"        # noVNC port
```

### 改變解析度

編輯 `docker-compose.kit-vnc.yml`：

```yaml
environment:
  DISPLAY_SIZE: "1920x1080"   # 改為 1920x1080
```

然後重新啟動容器：

```bash
docker-compose -f docker-compose.kit-vnc.yml restart kit-vnc
```

### GPU 設置

確保 GPU 支持已啟用：

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1                  # 使用 1 個 GPU
          capabilities: [gpu]
```

若要使用多個 GPU：

```yaml
count: 2                        # 使用 2 個 GPU
```

若要指定特定 GPU：

```yaml
device_ids: ['0', '1']          # 使用 GPU 0 和 1
```

---

## 📊 容器結構

```
Docker Stack
│
├─ kit-vnc (主容器)
│   ├─ Xvfb (虛擬顯示)
│   ├─ Fluxbox (視窗管理器)
│   ├─ x11vnc (VNC Server)
│   ├─ noVNC (Web VNC)
│   └─ Omniverse Kit (應用)
│
├─ postgres (數據庫)
├─ backend (Django API)
└─ frontend (Next.js)
```

---

## 🔍 監控和故障排除

### 查看容器狀態

```bash
docker-compose -f docker-compose.kit-vnc.yml ps
```

### 查看日誌

```bash
# Kit 日誌
docker-compose -f docker-compose.kit-vnc.yml logs kit-vnc

# 實時日誌
docker-compose -f docker-compose.kit-vnc.yml logs -f kit-vnc

# 特定時間段
docker-compose -f docker-compose.kit-vnc.yml logs --since 5m kit-vnc
```

### 進入容器

```bash
docker-compose -f docker-compose.kit-vnc.yml exec kit-vnc bash
```

### 查看容器內的日誌

```bash
# Xvfb 日誌
docker exec ran_kit_vnc tail -f /tmp/logs/xvfb.log

# x11vnc 日誌
docker exec ran_kit_vnc tail -f /tmp/logs/x11vnc.log

# noVNC 日誌
docker exec ran_kit_vnc tail -f /tmp/logs/novnc.log
```

---

## 🐛 常見問題

### Q1：無法連接 VNC

```
症狀：無法訪問 http://localhost:6080
原因：容器未成功啟動

解決：
docker-compose -f docker-compose.kit-vnc.yml logs kit-vnc
# 查看日誌中的錯誤信息
```

### Q2：GPU 無法識別

```
症狀：NVIDIA GPU 無法在容器中使用

前置檢查：
1. nvidia-docker 已安裝？
   docker run --rm --gpus all nvidia/cuda:12.4.1-runtime-ubuntu22.04 nvidia-smi

2. Docker Compose 配置正確？
   docker-compose -f docker-compose.kit-vnc.yml config | grep -A 5 "gpus"
```

### Q3：Kit 啟動失敗

```
症狀：容器運行但 Kit 進程不啟動

檢查：
1. scene_config.json 是否存在？
   docker exec ran_kit_vnc ls -la /home/omniverse/scene_config.json

2. Kit 檔案是否存在？
   docker exec ran_kit_vnc ls -la /home/omniverse/kit/

3. 查看詳細日誌：
   docker exec ran_kit_vnc cat /tmp/logs/kit.log | tail -50
```

### Q4：低性能或延遲

```
症狀：VNC 連接卡頓或滯後

解決方案：
1. 降低分辨率
   DISPLAY_SIZE: "1920x1080"

2. 增加容器資源限制
   deploy:
     resources:
       limits:
         cpus: '4'
         memory: 16g

3. 用客戶端代替 Web
   使用 VNC 客戶端而不是 noVNC Web
```

---

## 🔒 安全性注意

### 當前配置（開發用途）

```yaml
# ⚠️ 這些配置不適合生產
x11vnc:
  -nopw      # 無密碼
  -shared    # 允許多個連接
```

### 生產環境改進

```bash
# 1. 添加 VNC 密碼
x11vnc -nopw -forever ... -> x11vnc -passwd mysecretpass -forever ...

# 2. 限制連接來源
--localhost  # 只允許本地連接（在 docker-compose 中配置轉發）

# 3. 使用 VPN 或 SSH 隧道
ssh -L 5900:localhost:5900 user@host
# 然後連接到本地 localhost:5900

# 4. 防火牆規則
ufw allow from 192.168.1.0/24 to any port 6080
```

---

## 📈 性能優化

### 1. 啟用硬件加速

```yaml
environment:
  NVIDIA_DRIVER_CAPABILITIES: "compute,graphics,display"
  NVIDIA_VISIBLE_DEVICES: "all"
```

### 2. 限制日誌大小

已在 `docker-compose.kit-vnc.yml` 中配置：

```yaml
logging:
  options:
    max-size: "10m"
    max-file: "3"
```

### 3. 分配足夠的資源

```yaml
deploy:
  resources:
    limits:
      cpus: '4'           # 4 核心
      memory: 16g         # 16 GB
```

---

## 🗑️ 清理和重置

### 停止容器

```bash
docker-compose -f docker-compose.kit-vnc.yml down
```

### 停止並刪除卷（重置狀態）

```bash
docker-compose -f docker-compose.kit-vnc.yml down -v
```

### 完全清理

```bash
# 停止並刪除所有
docker-compose -f docker-compose.kit-vnc.yml down -v

# 刪除鏡像
docker image rm ran-omniverse-kit:latest

# 刪除未使用的卷
docker volume prune
```

---

## 🔄 工作流程

### 開發循環

```bash
# 1. 啟動環境
docker-compose -f docker-compose.kit-vnc.yml up -d

# 2. 在瀏覽器中訪問
open http://localhost:6080/vnc.html

# 3. 修改 scene_config.json
nano scene_config.json

# 4. 重新啟動 Kit
docker-compose -f docker-compose.kit-vnc.yml restart kit-vnc

# 5. 停止環境
docker-compose -f docker-compose.kit-vnc.yml down
```

---

## 📞 支持

若遇到問題，收集以下信息：

```bash
# 1. Docker 版本
docker --version
docker-compose --version

# 2. GPU 信息
nvidia-smi

# 3. 日誌
docker-compose -f docker-compose.kit-vnc.yml logs --tail 50

# 4. 容器詳情
docker inspect ran_kit_vnc
```

---

現在你可以：
1. ✅ 使用 Docker 容器化 Omniverse Kit
2. ✅ 通過 Web 瀏覽器遠程訪問
3. ✅ 使用 VNC 客戶端訪問
4. ✅ 完整的應用堆棧（數據庫 + 後端 + 前端）

開始使用：

```bash
docker-compose -f docker-compose.kit-vnc.yml up -d
# 訪問 http://localhost:6080/vnc.html
```
