#!/bin/bash
set -e

# Backend 啟動腳本，支援環境變數配置 IP 和 Port

# 從環境變數讀取配置，有預設值
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "[backend-entrypoint] Starting Django backend..."
echo "[backend-entrypoint] Host: $BACKEND_HOST"
echo "[backend-entrypoint] Port: $BACKEND_PORT"

# 執行 Django migrate
echo "[backend-entrypoint] Running migrations..."
python manage.py migrate

# 啟動 Daphne ASGI 伺服器
echo "[backend-entrypoint] Starting Daphne server..."
exec daphne -b "$BACKEND_HOST" -p "$BACKEND_PORT" main.asgi:application
