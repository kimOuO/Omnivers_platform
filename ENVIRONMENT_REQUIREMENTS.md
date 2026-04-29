# 🌐 Omniver Platform - 完整環境需求

## 📋 目錄
1. [主機環境需求](#主機環境需求)
2. [Docker 映像環境](#docker-映像環境)
3. [映像大小估計](#映像大小估計)
4. [服務間通信](#服務間通信)
5. [存儲需求](#存儲需求)

---

## 主機環境需求

### 💻 硬體最低配置

| 項目 | 最低 | 推薦 | 說明 |
|------|------|------|------|
| **CPU** | 4 cores | 8+ cores | 多容器並行處理 |
| **記憶體** | 16 GB | 32 GB+ | Kit 運行需要充足的 RAM |
| **GPU** | RTX A10 (24GB) | RTX A40 (48GB) 或更高 | **必須**，用於 3D 渲染 |
| **磁碟** | 50 GB SSD | 100 GB+ SSD | 包含鏡像、容器、資料庫 |
| **磁碟速度** | 5000 IOPS | 10000+ IOPS | 容器啟動和 DB 性能 |

### 🖥️ 作業系統

| 項目 | 版本 | 說明 |
|------|------|------|
| **Linux** | Ubuntu 22.04 LTS+ 或 Ubuntu 24.04+ | 推薦使用 Ubuntu |
| **NVIDIA Driver** | >= 525 | 支援 CUDA 12.6 |
| **NVIDIA CUDA** | 12.6 | 在 nvidia-cuda base 鏡像中已包含 |
| **NVIDIA cuDNN** | 8.9+ | 深度學習加速 |

### 📦 軟體先決條件

| 軟體 | 版本 | 用途 | 備註 |
|------|------|------|------|
| **Docker** | >= 20.10 | 容器執行環境 | 需要支援 `--gpus` flag |
| **Docker Compose** | >= 2.0 | 服務編排 | v1.29 可以，但 v2.0+ 推薦 |
| **NVIDIA Container Toolkit** | latest | GPU 支援（**必須**） | **關鍵**：無此無法使用 GPU |
| **Docker Build Kit** | 自動 | 多階段鏡像構建 | Docker 18.09+ 支援 |

#### 🔴 GPU 支援依賴關係

```
Docker >= 20.10 ──需要──> NVIDIA Container Toolkit
           ↓
   能執行 `docker run --gpus all`
           ↓
      Kit 容器可使用 GPU
```

**沒有 NVIDIA Container Toolkit = 無法使用 GPU = Kit 無法渲染 3D**

### 🔧 NVIDIA GPU 配置驗證

```bash
# 1️⃣ 檢查 GPU 驅動（主機層）
nvidia-smi
# 輸出應該顯示 GPU 型號和 CUDA 版本

# 2️⃣ 檢查 NVIDIA Container Toolkit 是否安裝
which nvidia-ctk
# 應該輸出 /usr/bin/nvidia-ctk

# 3️⃣ 檢查 Docker 是否能使用 GPU（最關鍵）
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi
# ✅ 如果看到 GPU 信息 = 配置正確
# ❌ 如果報錯 = 需要安裝/配置 NVIDIA Container Toolkit

# 4️⃣ 檢查 docker-compose 是否支援 GPU
docker compose version
# 應該是 v2.3+（支援 runtime: nvidia）
```

#### 常見問題

| 症狀 | 原因 | 解決方案 |
|------|------|--------|
| `docker: Error response from daemon: unknown flag: --gpus` | Docker < 20.10 | 升級 Docker |
| `nvidia-smi` 在容器內無法執行 | 沒安裝 NVIDIA Container Toolkit | 安裝 nvidia-container-toolkit |
| `runtime: nvidia not found` | docker-compose 配置錯誤 | 確認 NVIDIA Container Toolkit 已配置 |
| Kit 場景卡頓/黑屏 | GPU 未正確掛載 | 執行 nvidia-smi 檢查 GPU 可見性 |

---

## Docker 映像環境

### 📁 三個 Dockerfile

此項目有 **3 個獨立的 Dockerfile**：

| Dockerfile | 容器 | 用途 |
|------------|------|------|
| `kit/Dockerfile` | Kit（Omniverse） | 3D 場景渲染引擎 |
| `Omniver-RAN/Dockerfile` | Backend（Django） | REST API 伺服器 |
| `frontend/Dockerfile` | Frontend（Next.js） | Web 儀表板（生產） |

> **注意**：frontend/Dockerfile 是多階段生產構建，但在 docker-compose.yml 中被 `image: node:20-alpine` 覆蓋（開發用）。

---

### 🐳 Kit 容器（Omniverse）

**Dockerfile 路徑**: `kit/Dockerfile`

#### Base Image
```dockerfile
FROM nvidia/cuda:12.6.0-base-ubuntu24.04
```

| 組件 | 版本 | 用途 |
|------|------|------|
| **Base OS** | Ubuntu 24.04 | Linux 基礎系統 |
| **CUDA** | 12.6.0 | GPU 計算能力 |
| **cuDNN** | 預安裝 | 深度學習 |
| **NVIDIA Drivers** | 預安裝 | GPU 驅動 |

#### 系統依賴（行 6-12）
```bash
python3 python3-venv python3-pip        # Python 環境
xvfb x11vnc novnc websockify           # 虛擬顯示和遠程訪問
libglib2.0-0 libsm6 libxext6           # GUI 圖形庫
libxrender1 libxrandr2 libglu1-mesa    # OpenGL 支援
x11-utils x11-xserver-utils            # X11 工具
```

#### Python 環境（行 15-18）
```bash
Python 版本: 3.10（Ubuntu 24.04 預設）
venv 路徑: /opt/omniverse-env
Omniverse Kit 版本: 110.0.0.276876
PIP Index: https://pypi.nvidia.com
```

#### 虛擬顯示配置（entrypoint.sh）
```bash
Display: :99 (Xvfb 虛擬顯示)
分辨率: 1920x1080x24
DPI: 96
渲染模式: indirect GLX（+iglx GPU 加速）
```

#### 暴露端口

| 端口 | 協議 | 用途 |
|------|------|------|
| **8080** | HTTP | Kit REST API |
| **8081** | WebSocket | 場景快照推送（實時更新） |
| **5900** | VNC | 虛擬網路計算（原始 VNC） |
| **6080** | HTTP | noVNC Web 前端（瀏覽器 VNC） |

#### 環境變數（entrypoint.sh）
```bash
DISPLAY=:99                          # 虛擬顯示
OMNI_KIT_ALLOW_ROOT=1               # 允許 root 運行
CUDA_LAUNCH_BLOCKING=0              # CUDA 非同步執行
NVIDIA_VISIBLE_DEVICES=all          # 所有 GPU 可見
NVIDIA_DRIVER_CAPABILITIES=graphics,compute,utility  # GPU 功能
RAN_SCENE_CONFIG=/app/scene_config.json  # 場景配置文件
```

---

### 🖧 Backend 容器（Django）

**Dockerfile 路徑**: `Omniver-RAN/Dockerfile`
**Base Image**: `python:3.12-slim`
**Exposed Port**: 8000

### 🎨 Frontend 容器（Next.js）

**Dockerfile 路徑**: `frontend/Dockerfile`（多階段生產構建）
**Base Image**: `node:20-alpine`
**Exposed Port**: 3000

---

### 🗄️ Database 容器（PostgreSQL）

**映像**: `postgres:16-alpine`（無 Dockerfile，官方鏡像）

| 項目 | 值 |
|------|-----|
| **版本** | PostgreSQL 16 |
| **Base Image** | Alpine Linux 3.19 |
| **資料庫名** | ran_dt |
| **用戶** | ran |
| **密碼** | ran（開發用） |

#### 磁碟卷
```yaml
postgres-data: # 持久化數據卷
```

---

## 所有 Dockerfile 位置

```
Omniver_platform/
├── kit/
│   └── Dockerfile                    # ← Kit（Omniverse）
├── Omniver-RAN/
│   └── Dockerfile                    # ← Backend（Django）
└── frontend/
    └── Dockerfile                    # ← Frontend（Next.js）
```

**共 3 個 Dockerfile**

---

## 映像大小估計

### 各層大小分解

#### Kit 容器（最大）

| 層 | 大小 | 說明 |
|------|------|------|
| **nvidia/cuda:12.6.0-base-ubuntu24.04** | ~3.5 GB | Base 鏡像（CUDA + Ubuntu） |
| **系統依賴（apt）** | ~500 MB | Python、X11、圖形庫 |
| **Omniverse Kit（pip）** | ~1.6 GB | NVIDIA 官方發佈（緩存後） |
| **虛擬環境開銷** | ~100 MB | venv 元資料 |
| **專案文件（COPY）** | ~500 MB | extensions、assets、配置 |
| **中間層清理後** | **~5.8 GB** | 最終解壓鏡像 |

**最終 Kit 鏡像大小估計：5-6 GB**（取決於緩存和清理）

#### Backend 容器

| 層 | 大小 | 說明 |
|------|------|------|
| **python:3.10-slim** | ~150 MB | Base 鏡像 |
| **系統依賴** | ~200 MB | libpq、build tools |
| **Python 依賴** | ~300 MB | Django、Daphne、ORM 等 |
| **應用代碼** | ~50 MB | Django 項目 |
| **最終大小** | **~700 MB** | 總計 |

#### Frontend 容器

| 層 | 大小 | 說明 |
|------|------|------|
| **node:20-alpine** | ~150 MB | Base 鏡像 |
| **node_modules（構建）** | ~400 MB | npm 依賴（開發中） |
| **Next.js 編譯輸出** | ~100 MB | .next 構建輸出 |
| **最終大小（運行）** | **~200 MB** | 不包括 node_modules |

#### Database 容器

| 項目 | 大小 |
|------|------|
| **postgres:16-alpine** | ~70 MB |
| **PG 資料庫初始化** | ~20 MB |

### 總計磁碟需求

| 項目 | 大小 |
|------|------|
| **Kit 鏡像** | 5-6 GB |
| **Backend 鏡像** | 700 MB |
| **Frontend 鏡像** | 200 MB |
| **PostgreSQL 鏡像** | 70 MB |
| **所有鏡像總計** | **~6.5-7.5 GB** |
| **運行容器層** | 1-2 GB |
| **PostgreSQL 資料卷** | 初始 100 MB，可增至數 GB |
| **Extension 和 assets** | 500 MB |
| **快取和構建層** | 1-2 GB |
| **推薦總磁碟** | **50-100 GB** |

---

## 服務間通信

### 容器內部 DNS 路由（docker-compose）

```yaml
# docker-compose 內的服務可以通過服務名稱相互通信
# 無需 IP 地址或 localhost

Frontend ──(http://backend:8000)──> Backend
Backend  ──(http://kit:8080)────────> Kit
Backend  ──(postgresql://postgres:5432)──> Database
```

### 暴露到主機的端口

```yaml
Service    Port Mapping        URL
────────────────────────────────────────────────
Frontend   3001:3000          http://localhost:3001
Backend    8001:8000          http://localhost:8001
Kit API    8080:8080          http://localhost:8080
Kit WS     8081:8081          ws://localhost:8081
Kit VNC    5900:5900          vnc://localhost:5900
Kit noVNC  6080:6080          http://localhost:6080
PostgreSQL 5432:5432          postgresql://localhost:5432
```

---

## 存儲需求

### 磁碟配置

```bash
# 檢查磁碟空間
df -h /

# 監控當前使用
du -sh /var/lib/docker  # Docker 文件系統
du -sh /var/lib/docker/volumes  # 數據卷
```

### Volume 類型

| Volume | 容器 | 路徑 | 用途 | 持久化 |
|--------|------|------|------|--------|
| `postgres-data` | PostgreSQL | `/var/lib/postgresql/data` | 資料庫數據 | ✅ 是 |
| `frontend_node_modules` | Frontend | `/app/node_modules` | NPM 緩存 | ✅ 是 |
| `frontend_next_cache` | Frontend | `/app/.next` | Next.js 編譯快取 | ✅ 是 |
| 主機綁定 | Kit | `/home/mitlab/.../extensions` | Extensions 開發 | ✅ 是（主機） |
| 主機綁定 | Kit | `/home/mitlab/.../scene_config.json` | 場景配置 | ✅ 是（主機） |

### 推薦磁碟配置

```bash
# SSD 分區佈局（總 100 GB）
/             50 GB   # 根分區（OS + Docker）
/var/lib/docker 50 GB # Docker 數據（鏡像、容器、卷）
```

---

## 🚀 快速環境檢查清單

```bash
# 1. 檢查 GPU
nvidia-smi

# 2. 檢查 Docker
docker --version
docker compose --version
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi

# 3. 檢查磁碟
df -h /

# 4. 檢查網路
docker network ls

# 5. 檢查 Docker Daemon
docker info | grep -i "runtime"
```

---

## 📝 故障排除

### Kit 無法連接 GPU（最常見）

#### 情景 1：NVIDIA Container Toolkit 未安裝

```bash
# 症狀：docker run --gpus all 報錯

# 解決方案
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 驗證
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi
```

#### 情景 2：docker-compose.yml 中遺漏 GPU 配置

```yaml
# ❌ 錯誤
kit:
  image: nvidia/cuda:12.6.0-base-ubuntu24.04
  # 缺少 runtime 和環境變數

# ✅ 正確
kit:
  build:
    context: .
    dockerfile: kit/Dockerfile
  runtime: nvidia                    # ← 必須有
  environment:
    NVIDIA_VISIBLE_DEVICES: all      # ← 必須有
    NVIDIA_DRIVER_CAPABILITIES: all  # ← 必須有
```

#### 情景 3：Docker 版本過舊

```bash
# 檢查版本
docker --version

# 需要 >= 20.10
# 升級 Docker
sudo apt-get update
sudo apt-get install --only-upgrade docker-ce
```

### 磁碟空間不足

```bash
# 清理未使用的鏡像和卷
docker system prune -a --volumes

# 查看最大的鏡像
docker images --format "{{.Repository}}\t{{.Size}}" | sort -k2 -hr
```

### PostgreSQL 連接失敗

```bash
# 檢查 PostgreSQL 健康狀態
docker compose ps | grep postgres
docker compose logs postgres
```

---

**最後更新**: 2026-04-28
