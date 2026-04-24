#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

# shellcheck disable=SC1091
source .venv/bin/activate

python manage.py makemigrations ran
python manage.py migrate
