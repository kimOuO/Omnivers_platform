# 🚀 空機器快速部署指南

**前提**：新機器已安裝 Ubuntu 22.04/24.04 LTS，硬體資源符合要求

---

## 1️⃣ NVIDIA GPU 驅動安裝

```bash
# 檢查 GPU
lspci | grep -i nvidia

# 添加官方 PPA
sudo apt-get update
sudo apt-get install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall

# 驗證
nvidia-smi

# 確保 NVIDIA Driver >= 525，CUDA >= 12.0
```

---

## 2️⃣ Docker 安裝

```bash
# 移除舊版本
sudo apt-get remove -y docker docker-engine docker.io containerd runc

# 添加官方 repo
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安裝
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 驗證
docker --version  # >= 20.10
```

---

## 3️⃣ NVIDIA Container Toolkit 安裝（GPU 關鍵）

```bash
# 添加 NVIDIA GPG key
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# 添加 repo
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

# 安裝
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 配置 Docker daemon
sudo nvidia-ctk runtime configure --runtime=docker

# 重啟 Docker
sudo systemctl restart docker

# 驗證（最關鍵）
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi
# ✅ 如果看到 GPU 信息 = 成功
```

---

## 4️⃣ Docker Compose 安裝（可選，Docker 25+ 已內建）

```bash
# 檢查版本
docker compose version

# 若 < 2.0，手動安裝
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d'"' -f4)

sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose

sudo chmod +x /usr/local/bin/docker-compose

# 驗證
docker compose --version  # >= 2.0
```

---

## 5️⃣ 用戶權限配置（避免每次 sudo）

```bash
# 添加使用者至 docker 群組
sudo groupadd docker
sudo usermod -aG docker $USER

# 套用新群組（重新登入或執行）
newgrp docker

# 驗證（不需 sudo）
docker run hello-world
```

---

## 6️⃣ 拉取項目

```bash
# 進入工作目錄
cd /home/mitlab/XAPP_DT

# 克隆或更新項目
git clone <repository-url> Omnivers_platform
# 或
cd Omnivers_platform && git pull
```

---

## 7️⃣ 驗證環境

```bash
# 檢查磁碟空間（需要 50-100 GB）
df -h /

# 檢查 GPU
nvidia-smi

# 檢查 Docker GPU 支援
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi

# 檢查 Docker Compose
docker compose version
```

---

## 8️⃣ 構建鏡像

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform

# 構建所有鏡像（首次會下載 Kit ~1.6GB）
docker compose build

# 或指定只構建 kit
docker compose build kit
```

---

## 9️⃣ 啟動容器

```bash
# 啟動所有服務
docker compose up -d

# 等待初始化（5-10 分鐘）
docker compose logs -f kit

# 檢查服務狀態
docker compose ps
```

---

## 🔟 驗證服務

```bash
# 測試各服務
curl http://localhost:8080/          # Kit API
curl http://localhost:8001/api/v0.1/RAN/status  # Backend API
curl http://localhost:3001/          # Frontend

# 若返回 HTTP 200 或 HTML = 成功
```

---

## 🌐 訪問應用

| 服務 | URL | 用途 |
|------|-----|------|
| **前端儀表板** | http://localhost:3001 | Web UI |
| **3D 場景（VNC Web）** | http://localhost:6080/vnc.html | 虛擬顯示 |
| **Kit API** | http://localhost:8080 | REST API |
| **PostgreSQL** | postgresql://localhost:5432 | 數據庫 |

---

## ❌ 常見問題排查

| 症狀 | 解決 |
|------|------|
| `docker: unknown flag: --gpus` | 升級 Docker >= 20.10 |
| 容器無法訪問 GPU | 重新執行 `nvidia-ctk runtime configure && systemctl restart docker` |
| 磁碟空間不足 | 清理：`docker system prune -a --volumes` |
| 容器無法啟動 | 檢查日誌：`docker compose logs kit` |
| Kit 黑屏 | GPU 未掛載，檢查 `nvidia-smi` 在容器內是否有效 |

---

**預計總時間**：15-20 分鐘（首次下載 Kit 較久）
