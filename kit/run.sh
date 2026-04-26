#!/usr/bin/env bash
# Launch the long-running RAN Omniverse Server.
#
# Pre-requisites:
#   - ~/omniverse-env has pip-installed `omniverse-kit` 110.0.0
#   - kit-app-template has been built once (for extscache)
#   - DISPLAY is set (for local / VNC viewport)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
KIT_FILE="${HERE}/ran_server.kit"

# Scene config for mitlab.ran.scene.builder (stored in project root).
# Override via env before calling this script if needed.
export RAN_SCENE_CONFIG="${RAN_SCENE_CONFIG:-${HERE}/../scene_config.json}"

# Virtual display for rendering (Xvfb).
# Use :88 for local VNC via x11vnc, or set via env before calling if needed.
export DISPLAY="${DISPLAY:-:88}"

# Activate venv if not already
if [ -z "${VIRTUAL_ENV:-}" ]; then
  if [ -f "${HOME}/omniverse-env/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "${HOME}/omniverse-env/bin/activate"
  else
    echo "[run.sh] WARN: ~/omniverse-env not found; assuming omniverse-kit is on PATH"
  fi
fi

echo "[run.sh] RAN_SCENE_CONFIG=${RAN_SCENE_CONFIG}"
echo "[run.sh] Launching Kit with ${KIT_FILE}"

# Pass the .kit path as a positional argument (not --/app/file/default=,
# which is "USD file to open" and makes Kit auto-quit since no run loop is defined).
# Force window display for VNC remote viewing
exec python -m omni.kit_app "${KIT_FILE}" \
  --/app/window/show=true \
  --/app/window/width=1920 \
  --/app/window/height=1080 \
  "$@"
