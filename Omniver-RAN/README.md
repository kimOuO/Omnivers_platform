# 🔌 Omniver-RAN - Django Backend

RAN Digital Twin 的資料匯流排和 REST API 層。處理場景狀態、訊號接收、資料持久化。

---

## 概述

**Omniver-RAN** 是遵循 `backend_rule.md` 的 Django 應用，提供：

- **REST API**：POST-only，格式 `/api/v0.1/{System}/{Module}/{Component}/{Element}`
- **資料模型**：Scene、Building、gNB、UE、Signal 等
- **訊號接收**：透過 `SignalIngestor` 接收外部訊號
- **Kit 互動**：與 Omniverse Kit 伺服器通信
- **資料持久化**：PostgreSQL 資料庫儲存

---

## 啟動方式

### 透過 Docker Compose（推薦）

```bash
# 啟動所有服務，包括 backend
docker compose up -d

# 單獨重啟 backend
docker compose restart backend
```

### 檢查 Backend 狀態

```bash
# 查看日誌
docker compose logs -f backend

# 測試 API
curl http://localhost:8001/api/v0.1/RAN/status

# 進入容器
docker exec -it omniver_backend bash
```

---

## 專案結構

```
Omniver-RAN/
├── Dockerfile              Backend 容器定義
├── manage.py              Django 管理工具
├── requirements/          依賴清單
│   ├── base.txt          共用依賴
│   ├── local.txt         本地開發依賴
│   ├── production.txt     生產環境依賴
│   └── test.txt          測試依賴
├── shell/                管理腳本
│   ├── init_project.sh   初始化
│   └── run_migrations.sh 資料庫遷移
├── main/                Django 專案根目錄
│   ├── asgi.py          ASGI 應用
│   ├── wsgi.py          WSGI 應用（生產）
│   ├── urls.py          主路由
│   ├── settings/        環境配置
│   │   ├── base.py      基礎設定
│   │   ├── local.py     本地開發
│   │   └── production.py 生產環境
│   ├── utils/           基礎設施工具
│   │   ├── env_loader.py 環境變數載入
│   │   ├── logger.py     日誌配置
│   │   ├── response.py   響應格式化
│   │   └── db_router.py  資料庫路由
│   └── apps/ran/        RAN 應用（核心邏輯）
│       ├── models/      資料模型
│       ├── serializers/ 資料驗證和轉換
│       ├── actors/      HTTP 處理器
│       ├── services/    業務邏輯
│       │   ├── business/
│       │   ├── common/
│       │   └── optional/
│       ├── api/         API 路由
│       └── tests/       測試
├── logs/                日誌檔案
└── README.md           本檔案
```

---

## Request Chain（請求流程）

所有 HTTP 請求遵循統一的流程：

```
Client
  ↓
POST /api/v0.1/RAN/{Module}/{Component}/{Element}
  ↓
main/urls.py (路由聚合)
  ↓
main/apps/ran/api/urls.py (API 路由綁定)
  ↓
Actor.function (HTTP 處理和業務編排)
  ↓
Serializer (資料驗證和轉換)
  ↓
Business Service (單一業務操作)
  ↓
Common Service (通用工具：UUID、時間戳)
  ↓
Model (資料庫操作)
  ↓
PostgreSQL
```

**關鍵原則**：
- 只使用 POST 方法
- Actor 負責編排，不直接操作資料庫
- Service 提供通用方法（接受 model_class 參數）
- Serializer 驗證輸入

詳見 `../backend_rule.md`

---

## 主要 API 端點

### 場景管理

```bash
# 查詢場景狀態
curl -X POST http://localhost:8001/api/v0.1/RAN/Scene/SceneStateReader/read \
  -H "Content-Type: application/json" -d '{}'

# 構建場景
curl -X POST http://localhost:8001/api/v0.1/RAN/Scene/SceneBuilder/create \
  -H "Content-Type: application/json" \
  -d '{"name":"test_scene","buildings":6,"gnbs":3,"ues":5}'
```

### 訊號接收

```bash
# 接收訊號資料
curl -X POST http://localhost:8001/api/v0.1/RAN/Ingest/SignalIngestor/create \
  -H "Content-Type: application/json" \
  -d '{
    "ts":"2026-04-25T10:00:00Z",
    "signals":[{
      "ue_name":"UE_1",
      "serving_cell":"gNB_Macro_NW",
      "rsrp_dbm":-78.2,
      "sinr_db":12.5
    }]
  }'
```

詳細 API 文檔見 `../docs/ingest_api.md`

---

## 容器配置

### docker-compose.yml 中的 Backend 設定

```yaml
backend:
  build:
    context: ./Omniver-RAN
    dockerfile: Dockerfile
  container_name: omniver_backend
  ports:
    - "8001:8000"  # 主機:容器 (Daphne ASGI 伺服器)
  environment:
    DJANGO_SECRET_KEY: dev-change-me
    DJANGO_DEBUG: "True"
    DJANGO_ALLOWED_HOSTS: "*"
    DJANGO_SETTINGS_MODULE: main.settings.local
    DB_HOST: postgres
    DB_PORT: "5432"
    DB_NAME: ran_dt
    DB_USER: ran
    DB_PASSWORD: ran
    HTTP_KIT_HOST: kit              # 連接 Kit 伺服器
    HTTP_KIT_PORT: "8080"
    WS_KIT_PORT: "8081"
    LOG_LEVEL: INFO
  depends_on:
    postgres:
      condition: service_healthy
    kit:
      condition: service_started
  command: >
    sh -c "python manage.py migrate &&
           daphne -b 0.0.0.0 -p 8000 main.asgi:application"
  volumes:
    - ./Omniver-RAN:/app  # 熱重載
  restart: unless-stopped
```

---

## 開發和調試

### 進入 Backend 容器

```bash
docker exec -it omniver_backend bash
```

### 執行 Django 指令

```bash
# 查看資料庫狀態
docker exec omniver_backend python manage.py showmigrations

# 執行特定遷移
docker exec omniver_backend python manage.py migrate ran

# 建立資料庫
docker exec omniver_backend python manage.py migrate

# Django shell（互動式）
docker exec -it omniver_backend python manage.py shell

# 建立超級使用者（如需）
docker exec omniver_backend python manage.py createsuperuser
```

### 檢查日誌

```bash
# 實時日誌
docker compose logs -f backend

# 查看錯誤
docker compose logs backend | grep ERROR

# 完整日誌
docker compose logs backend > backend.log
```

### 連接資料庫

```bash
# 進入 Postgres
docker exec -it omniver_postgres psql -U ran -d ran_dt

# 查詢表
\dt                    # 列出所有表
\d ran_scene          # 查看 ran_scene 表結構

# SQL 查詢
SELECT * FROM ran_scene LIMIT 5;
```

---

## 架構規範

後端遵循 `backend_rule.md` 中的鐵則：

### 禁止事項

- ❌ 使用 GET/PUT/PATCH/DELETE（只用 POST）
- ❌ 直接使用 `os.getenv()`（使用 `env_loader`）
- ❌ 在 Service 中硬編碼 Model 名稱
- ❌ 為每個 Model 寫專門的 Service 方法
- ❌ 在 Utils 中放業務邏輯

### 必須做的事

- ✅ 所有環境變數透過 `env_loader` 讀取
- ✅ Serializer 區分 Read/Write
- ✅ Business Service 提供通用方法
- ✅ Actor 負責編排和 Transaction 控制
- ✅ Service 不直接處理 HTTP

---

## 問題排除

### Backend 無法連接到 Database

```bash
# 檢查 Postgres 狀態
docker compose ps postgres

# 測試連接
docker exec omniver_backend python manage.py shell
>>> from django.db import connection
>>> cursor = connection.cursor()
>>> cursor.execute("SELECT 1")
True

# 查看詳細錯誤
docker compose logs backend | grep -i postgres
```

### Backend 無法連接到 Kit

```bash
# 測試連接
docker exec omniver_backend curl http://kit:8080/

# 查看錯誤
docker compose logs backend | grep -i "kit"

# 檢查環境變數
docker exec omniver_backend env | grep KIT
```

### 遷移失敗

```bash
# 查看遷移狀態
docker exec omniver_backend python manage.py showmigrations

# 重新執行遷移
docker exec omniver_backend python manage.py migrate --verbosity 2

# 重置單個應用（謹慎）
docker exec omniver_backend python manage.py migrate ran zero
docker exec omniver_backend python manage.py migrate ran
```

---

## 性能監控

### 檢查 Backend 資源使用

```bash
# CPU 和記憶體
docker stats omniver_backend

# 詳細進程信息
docker exec omniver_backend ps aux

# 連接數
docker exec omniver_backend netstat -an | grep ESTABLISHED | wc -l
```

---

## 維護

### 備份資料庫

```bash
# 匯出資料
docker exec omniver_postgres pg_dump -U ran -d ran_dt > backup.sql

# 壓縮備份
docker exec omniver_postgres pg_dump -U ran -d ran_dt | gzip > backup.sql.gz
```

### 恢復資料庫

```bash
# 從備份恢復
docker exec -i omniver_postgres psql -U ran -d ran_dt < backup.sql
```

### 重建容器

```bash
# 完全重建（不使用快取）
docker compose build --no-cache backend

# 重啟服務
docker compose up -d backend
```

---

## 相關資源

- **主文檔**：../README.md
- **Docker 操作**：../DOCKER_QUICKSTART.md
- **架構規範**：../backend_rule.md（必讀）
- **API 文檔**：../docs/ingest_api.md
- **場景配置**：../SCENE_CONFIG_GUIDE.md

---

## 重要提醒

1. **環境變數**：所有配置透過環境變數管理（見 docker-compose.yml）
2. **遷移**：自動執行 migrations（見 docker-compose.yml 的 command）
3. **ASGI**：使用 Daphne ASGI 伺服器（支援 HTTP 和 WebSocket）
4. **日誌**：啟用 DEBUG 模式便於開發（見 DJANGO_DEBUG=True）

---

最後更新：2026-04-25
