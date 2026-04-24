#!/usr/bin/env bash
# One-shot bootstrap for local dev.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements/local.txt

if [ ! -f .env ]; then
  cp .env.sample .env
  echo "[init_project] created .env from sample"
fi

echo "[init_project] done. Next: ./shell/run_migrations.sh"
