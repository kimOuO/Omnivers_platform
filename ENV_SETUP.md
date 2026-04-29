# 環境變數配置指南（已優化）

## 📋 概述

Omniverse_platform 現已支持通過 `.env` 檔案配置部署參數。

**核心原則**：修改 `.env` 檔案，無需手動編輯 `docker-compose.yml`

---

## 🎯 快速開始

### 開發環境（預設）

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform

# 直接啟動
docker compose up -d
```

### 網路部署

```bash
# 編輯 .env
vim .env

# 改以下值
SERVER_IP=192.168.1.101
DJANGO_DEBUG=False
DB_PASSWORD=strong-password

# 重啟
docker compose down
docker compose up --build -d
```

---

## 📝 .env 檔案配置

### 位置

```
/home/mitlab/XAPP_DT/Omnivers_platform/.env
```

### 部署設定

```bash
# 改這個 IP，所有 Frontend URL 自動更新
SERVER_IP=localhost              # localhost / 192.168.1.x / domain.com

# 埠號配置
FRONTEND_PORT=3001
BACKEND_PORT=8001
DB_PORT=5432
```

### Django 配置

```bash
# 開發環境
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=dev-change-me
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# 生產環境（需改）
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=your-secure-key-here
DJANGO_ALLOWED_HOSTS=192.168.1.101,localhost
```

### 數據庫配置

```bash
DB_HOST=postgres                 # Docker 內部 DNS，勿改
DB_NAME=ran_dt
DB_USER=ran
DB_PASSWORD=ran                  # 生產環境改成強密碼
```

### Kit 配置

```bash
HTTP_KIT_HOST=kit               # Docker 內部 DNS，勿改
HTTP_KIT_PORT=8080
WS_KIT_PORT=8081
```

### 日誌

```bash
LOG_LEVEL=INFO                  # 開發用，生產改 WARNING
```

---

## 🔄 自動更新的配置

修改 `.env` 後，以下配置會**自動生成**：

```
SERVER_IP=192.168.1.101 + BACKEND_PORT=8001
    ↓
NEXT_PUBLIC_API_BASE_URL: http://192.168.1.101:8001
NEXT_PUBLIC_WS_URL: ws://192.168.1.101:8001/api/v0.1/RAN/UE/live
```

**無需手動編輯 docker-compose.yml！**

---

## 📊 完整配置範例

### 本機開發

```bash
SERVER_IP=localhost
FRONTEND_PORT=3001
BACKEND_PORT=8001
DB_PORT=5432

DJANGO_SECRET_KEY=dev-change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DB_HOST=postgres
DB_NAME=ran_dt
DB_USER=ran
DB_PASSWORD=ran

HTTP_KIT_HOST=kit
HTTP_KIT_PORT=8080
WS_KIT_PORT=8081

LOG_LEVEL=INFO
```

### 內網部署（192.168.1.101）

```bash
SERVER_IP=192.168.1.101
FRONTEND_PORT=3001
BACKEND_PORT=8001
DB_PORT=5432

DJANGO_SECRET_KEY=your-secure-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=192.168.1.101,localhost

DB_HOST=postgres
DB_NAME=ran_dt
DB_USER=ran
DB_PASSWORD=secure-password

HTTP_KIT_HOST=kit
HTTP_KIT_PORT=8080
WS_KIT_PORT=8081

LOG_LEVEL=WARNING
```

---

## ✅ 驗證配置

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform

# 1. 檢查 .env 檔案
cat .env

# 2. 驗證 docker-compose 解析
docker compose config | grep -E "API_BASE|WS_URL"
# 應該看到替換後的實際值

# 3. 啟動並檢查
docker compose up -d
docker compose ps
# 4 個容器都應該是 Up 狀態

# 4. 檢查日誌
docker compose logs -f backend
```

---

## 🔐 生成強密碼和密鑰

### Django Secret Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 數據庫密碼

```bash
openssl rand -base64 16
```

---

## 📋 環境檢查清單

部署前檢查：
- [ ] 確認 SERVER_IP（localhost / IP / 域名）
- [ ] 確認 DJANGO_DEBUG（開發 True，生產 False）
- [ ] 若改密碼，確認 DB_PASSWORD 已更新
- [ ] 若改密鑰，確認 DJANGO_SECRET_KEY 已更新

部署後檢查：
- [ ] `docker compose ps` - 4 個容器都是 Up
- [ ] `curl http://localhost:8001/api/v0.1/RAN/SimSession/PlaybackController/list`
- [ ] 瀏覽器打開 `http://localhost:3001`

---

## 🚀 常見命令

```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform

# 啟動
docker compose up -d

# 查看日誌
docker compose logs -f backend

# 重啟
docker compose restart

# 停止
docker compose down

# 清理並重新啟動（改了 .env 後用這個）
docker compose down
docker compose up --build -d
```

---

## 🆘 常見問題

| 問題 | 解決 |
|------|------|
| 容器起不來 | 檢查 .env 語法（無空格：key=value） |
| Frontend 連不上 API | 檢查 SERVER_IP 和 BACKEND_PORT 是否正確 |
| 數據庫連接失敗 | 確認 postgres 容器已啟動（docker compose ps） |
| 改了 .env 沒有效果 | 需要 `docker compose up --build -d` 重新構建 |

---

**最後更新**：2026-04-29（已優化為 .env 配置版本）
