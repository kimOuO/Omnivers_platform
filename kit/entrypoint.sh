#!/usr/bin/env bash
# Don't use 'set -e' — it causes infinite restart loops
trap "pkill -P $$" EXIT

echo "[kit-entrypoint] Starting Omniverse Kit..."

# Use fixed display
export DISPLAY=:99
echo "[kit-entrypoint] Using display $DISPLAY"

# Clean up any stale lock files
rm -f /tmp/.X99-lock /tmp/.X11-unix/99 2>/dev/null || true

# Start Xvfb with indirect GLX for GPU rendering in virtual environment
echo "[kit-entrypoint] Starting Xvfb..."
Xvfb $DISPLAY +iglx +extension GLX -screen 0 1920x1080x24 +extension RENDER +extension Composite +extension XFIXES -dpi 96 > /tmp/xvfb.log 2>&1 &
XVFB_PID=$!
sleep 3

# Verify Xvfb started
if ! ps -p $XVFB_PID > /dev/null 2>&1; then
    echo "ERROR: Xvfb failed to start. Check /tmp/xvfb.log"
    cat /tmp/xvfb.log
    sleep 60  # Keep container alive for debugging
    exit 1
fi
echo "[kit-entrypoint] Xvfb started (PID: $XVFB_PID)"

# Configure display (non-critical, ignore errors)
xrandr --newmode "1920x1080_60" 173.00 1920 2048 2248 2576 1080 1083 1088 1120 -hsync +vsync 2>/dev/null || true
xrandr --addmode default "1920x1080_60" 2>/dev/null || true
xrandr --output default --mode "1920x1080_60" 2>/dev/null || true

# Start VNC with improved settings for complex scenes
echo "[kit-entrypoint] Starting x11vnc..."
nohup x11vnc -display $DISPLAY -nopw -forever -shared -rfbport 5900 \
    -noxdamage -noscr -nowf -noxfixes -ncache 0 -noshm \
    -q -bg > /tmp/x11vnc.log 2>&1 &
X11VNC_PID=$!
sleep 2
if ps -p $X11VNC_PID > /dev/null 2>&1; then
    echo "[kit-entrypoint] x11vnc started (PID: $X11VNC_PID)"
else
    echo "[kit-entrypoint] WARNING: x11vnc may have failed. Log:"
    cat /tmp/x11vnc.log
fi

# Start noVNC (websockify)
echo "[kit-entrypoint] Starting noVNC WebSocket proxy..."
/usr/bin/python3 /usr/bin/websockify --web /usr/share/novnc 6080 localhost:5900 > /tmp/websockify.log 2>&1 &
WEBSOCKIFY_PID=$!
sleep 2

if ! ps -p $WEBSOCKIFY_PID > /dev/null 2>&1; then
    echo "WARNING: websockify may have failed. Check /tmp/websockify.log"
    cat /tmp/websockify.log
    # Continue anyway — user can still use VNC directly
fi
echo "[kit-entrypoint] noVNC ready on port 6080 (or VNC on 5900)"

# Start Kit with EULA auto-accept via Python
echo "[kit-entrypoint] Starting Kit app..."
export RAN_SCENE_CONFIG=/app/scene_config.json
export OMNI_KIT_ALLOW_ROOT=1

# GPU rendering configuration
export CUDA_LAUNCH_BLOCKING=0
export NVIDIA_VISIBLE_DEVICES=all
export NVIDIA_DRIVER_CAPABILITIES=graphics,compute,utility

source /opt/omniverse-env/bin/activate

# Run Kit with input patching for EULA and prompts
echo "[kit] Launching Kit with auto-EULA..."
python << 'EOFPYTHON'
import sys
import builtins

# Patch input() to auto-answer EULA and press-any-key prompts
_orig_input = builtins.input
def auto_input(prompt=""):
    if any(x in prompt.lower() for x in ["eula", "accept", "agree", "terms"]):
        print(f"{prompt}Yes")
        return "Yes"
    if "press" in prompt.lower() and "key" in prompt.lower():
        print(f"{prompt}")
        return ""
    return _orig_input(prompt)

builtins.input = auto_input

# Run Kit module
import runpy
sys.argv = ['kit', '/app/kit/ran_server.kit',
            '--/app/window/show=true',
            '--/app/window/width=1920',
            '--/app/window/height=1080',
            '--/app/window/uiScaleFactor=1',
            '--/exts/omni.kit.window.content_browser/show=false',
            '--/exts/omni.kit.window.property/show=false',
            '--/exts/omni.kit.window.stage/show=false',
            '--/exts/omni.kit.viewport.window/show=true',
            '--/rtx-transactionlogging=0']
runpy.run_module('omni.kit_app', run_name='__main__')
EOFPYTHON
