# 🌐 Omniver Platform - RAN Digital Twin 控制平台

## 專案介紹

**Omniver** 是一個完整容器化的 **RAN（無線接取網路）數位孿生平台**，用於 xApp 交付驗證和訊號追蹤。

### 核心功能

- 🏗️ **3D 場景構建**：使用 NVIDIA Omniverse Kit 構建 RAN 網路環境（基站、使用者設備）
- 📊 **訊號模擬**：外部系統輸入訊號（RSRP/SINR），實時顯示在 3D 場景中
- 🎮 **交互式儀表板**：Web 前端查看狀態、配置場景、追蹤軌跡
- 🎯 **API 驅動**：REST API 支援自動化測試和外部系統整合
- 🚀 **完全容器化**：一鍵啟動所有服務，支援 GPU 加速

### 適用場景

| 場景 | 說明 |
|------|------|
| xApp 開發驗證 | 在模擬 RAN 環境中測試 xApp |
| 訊號分析 | 實時可視化 RSRP/SINR 等無線指標 |
| 網路演練 | 模擬基站切換、覆蓋變化等場景 |
| 教學研究 | 5G/6G 網路架構和訊號傳播的視覺化學習 |

---

## 系統要求與版本

### 環境需求

| 項目 | 最低版本 | 推薦版本 | 說明 |
|------|---------|---------|------|
| **Docker** | 20.10 | 25.0+ | 容器執行環境 |
| **Docker Compose** | 1.29 | 2.20+ | 服務編排工具 |
| **NVIDIA Docker Runtime** | - | latest | GPU 支援（必須） |
| **NVIDIA CUDA** | 12.0 | 12.6+ | GPU 計算 |
| **GPU 記憶體** | 24GB | 40GB+ | 推薦 A40 或更高 |
| **磁碟空間** | 20GB | 50GB+ | 包含 Kit (~1.6GB) + 映像 + 資料 |

### 核心依賴

| 服務 | 版本 | 映像 | 說明 |
|------|------|------|------|
| **PostgreSQL** | 16 | `postgres:16-alpine` | 資料庫 |
| **Python** | 3.10 | Ubuntu 22.04 | Django backend 執行環境 |
| **Django** | 4.2+ | 自建 | REST API 伺服器 |
| **Node.js** | 20 | `node:20-alpine` | Next.js 執行環境 |
| **Next.js** | 14+ | 自建 | Web 前端框架 |
| **Omniverse Kit** | 106.0.3 | 自建 | 3D 場景渲染引擎 |
| **NVIDIA CUDA** | 12.6 | `nvidia/cuda:12.6.0-base-ubuntu22.04` | GPU 計算 |

---

## 📦 安裝前置軟體

### 安裝 Docker

```bash
# 1. 移除舊版本（如有）
sudo apt-get remove docker docker-engine docker.io containerd runc

# 2. 更新套件清單
sudo apt-get update

# 3. 安裝相依套件
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 4. 添加 Docker 官方 GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 5. 添加 Docker repository
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 6. 安裝 Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 7. 驗證安裝
docker --version
```

### 安裝 Docker Compose

```bash
# 檢查最新版本
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d'"' -f4)

# 下載並安裝
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose

# 賦予執行權限
sudo chmod +x /usr/local/bin/docker-compose

# 驗證安裝
docker compose --version
```

### 加入使用者群組（可選，避免每次都 sudo）

```bash
# 創建 docker 群組（如不存在）
sudo groupadd docker

# 加入目前使用者
sudo usermod -aG docker $USER

# 使用新群組（重新登入或執行此命令）
newgrp docker

# 驗證（不需要 sudo）
docker run hello-world
```

---

### 檢查前置條件

```bash
# 檢查 Docker
docker --version    # Docker 20.10+
docker compose --version  # Docker Compose 2.0+

# 檢查 NVIDIA GPU 和 Runtime
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi

# 檢查磁碟
df -h /  # 需要 50GB+ 空餘空間
```

---

## 🔧 GPU 環境配置（必要）

如果你還**沒有配置 NVIDIA Docker Runtime**，執行以下步驟：

### 1️⃣ 檢查是否已配置

```bash
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi
```

- ✅ **能看到 GPU 信息** → 已配置，跳過下面步驟
- ❌ **顯示錯誤** → 需要配置，繼續下面步驟

### 2️⃣ 安裝 NVIDIA Container Toolkit

複製以下指令一次執行：

```bash
# 1. 添加 NVIDIA GPG key
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# 2. 添加 repository
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

# 3. 更新套件清單
sudo apt-get update

# 4. 安裝 NVIDIA Container Toolkit
sudo apt-get install -y nvidia-container-toolkit

# 5. 配置 Docker 使用 nvidia runtime
sudo nvidia-ctk runtime configure --runtime=docker

# 6. 重啟 Docker daemon
sudo systemctl restart docker
```

### 3️⃣ 驗證配置成功

```bash
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi
```

應該能看到 **GPU 信息**（型號、顯存、Driver 版本），表示配置成功！

> **注意**：這一步只需執行一次。配置完成後，所有 Docker 容器都能自動使用 GPU。

---

## 🚀 快速啟動

### 1️⃣ 進入專案目錄

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform
```

### 2️⃣ 一鍵啟動所有服務

```bash
docker compose up -d
```

首次執行會：
- 構建 backend 容器映像（~3-5 分鐘）
- 下載 Omniverse Kit（~1.6GB）
- 初始化 PostgreSQL 資料庫
- 啟動所有 4 個服務

### 3️⃣ 等待初始化完成

```bash
# 檢查服務狀態
docker compose ps

### 4️⃣ 驗證啟動成功

```bash
# 查看容器狀態
docker compose ps

# 測試各服務
curl http://localhost:8080/          # Kit API
curl http://localhost:8001/api/v0.1/RAN/status  # Backend API
curl http://localhost:3001/          # Frontend
```

---

## 🌐 訪問服務

### Web 前端（Next.js Dashboard）

```
http://localhost:3001
http://10.3.0.217:3001/
```

**功能**：
- 查看場景狀態
- 配置基站和使用者設備
- 編輯軌跡路徑
- 實時監控訊號指標

### VNC Web（虛擬顯示 - 3D 場景）

```
http://localhost:6080/vnc.html
http://10.3.0.217:6080/vnc.html
```

**功能**：
- 實時查看 3D 場景
- 觀察 UE 移動和基站覆蓋
- 視覺化 RSRP/SINR 浮標


## 🛑 停止服務

### 停止容器（保留資料庫）

```bash
docker compose down
```

資料庫資料會保留，下次啟動時恢復。

## 📁 項目結構

```
Omniver_platform/
├── 📄 docker-compose.yml       一鍵啟動所有服務（主文件）
├── 📄 DOCKER_QUICKSTART.md     詳細快速啟動指南
├── 📄 SCENE_CONFIG_GUIDE.md    場景配置細節指南
├── 📄 backend_rule.md          Django 架構鐵則和規範
├── 📄 frontend_rule.md         Next.js 架構鐵則和規範
│
├── 📁 kit/                     Omniverse Kit 配置
│   ├── Dockerfile              Kit 容器定義
│   ├── entrypoint.sh           啟動腳本
│   └── ran_server.kit          Kit 配置檔
│
├── 📁 extensions/              Kit Python 擴展
│   ├── mitlab.ran.api/         HTTP API 接口（port 8080）
│   ├── mitlab.ran.scene.builder/ 場景構建和動畫
│   └── mitlab.ran.labels/      訊號浮標顯示
│
├── 📁 Omniver-RAN/             Django backend 專案
│   ├── Dockerfile              Backend 容器定義
│   ├── manage.py               Django 管理指令
│   ├── main/
│   │   └── apps/ran/           RAN 應用（models/serializers/actors/services）
│   ├── requirements/           依賴清單
│   └── shell/                  初始化和遷移腳本
│
├── 📁 frontend/                Next.js 前端專案
│   ├── Dockerfile              Frontend 容器定義
│   ├── app/                    App Router 頁面
│   ├── components/             React 元件
│   ├── services/               API 呼叫
│   ├── package.json            NPM 依賴
│   └── next.config.js          Next.js 配置
│
├── 📁 assets/                  3D 場景資產
│   ├── ran/                    RAN 網路模型
│   └── Assets/                 角色和道具
│
├── 📁 docs/                    文檔和參考
│   ├── ingest_api.md           訊號輸入 API 合約
│   ├── s4_smoke_test.sh        系統驗證腳本
│   └── sequence_diagrams/      用例時序圖
│
└── 📁 .git/                    Git 版本控制
```

---