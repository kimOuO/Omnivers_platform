# Omniver-RAN (Django Backend)

RAN Digital Twin 的資料匯流排 / API 層。**不做訊號計算**（訊號值由外部透過 ingest API 送入）。

- Platform: **Omniver**
- System: **RAN**
- Repo name satisfies `{platform}-{system}` per backend_rule.md 1-1.

## Request Chain

```
Client
  → main/urls.py
  → main/apps/ran/api/urls.py
  → Actor.function
  → Serializer (驗證)
  → Business Service (SqlDb / Kit)
  → Common Service (UUID / Timestamp / Validation)
  → Model
```

## API 格式

URL 一律 POST，格式：`/api/v0.1/{System}/{Module}/{Component}/{Element}`

主要端點請見 `../docs/ingest_api.md` 與 `main/apps/ran/api/urls.py`。

## 啟動

```bash
# 1. Postgres
docker compose up -d postgres

# 2. venv + deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/local.txt

# 3. env
cp .env.sample .env

# 4. Migration
./shell/run_migrations.sh
# 或手動：
# python manage.py makemigrations ran
# python manage.py migrate

# 5. 啟動
python manage.py runserver 0.0.0.0:8001
```
