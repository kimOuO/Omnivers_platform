#!/bin/bash
# Omniverse Kit startup script for Docker with VNC

set -e

DISPLAY=${DISPLAY:-":99"}
SCENE_CONFIG=${SCENE_CONFIG:-"/home/omniverse/scene_config.json"}
KIT_FILE=${KIT_FILE:-"/home/omniverse/kit/ran_server.kit"}

echo "========================================="
echo "RAN Omniverse Kit - Docker VNC Startup"
echo "========================================="
echo ""
echo "✓ DISPLAY=$DISPLAY"
echo "✓ SCENE_CONFIG=$SCENE_CONFIG"
echo "✓ KIT_FILE=$KIT_FILE"
echo ""

# Wait for Xvfb to be ready
echo "⏳ Waiting for Xvfb to start..."
for i in {1..30}; do
    if DISPLAY=$DISPLAY xdpyinfo > /dev/null 2>&1; then
        echo "✓ Xvfb is ready!"
        break
    fi
    echo -n "."
    sleep 1
done

# Wait for Fluxbox to be ready
echo "⏳ Waiting for Fluxbox to start..."
sleep 3

# Check if scene_config.json exists
if [ ! -f "$SCENE_CONFIG" ]; then
    echo "⚠️  Creating default scene_config.json..."
    cat > "$SCENE_CONFIG" << 'EOF'
{
  "environment": {"usd": ""},
  "ground": {"material": "grass", "size": [1000, 1000]},
  "buildings": [
    {"name": "Building_1", "position": [0, 0, 0], "size": [50, 30, 100], "material": "concrete"}
  ],
  "gnbs": [
    {"name": "gNB_1", "position": [200, 200, 50], "frequency_ghz": 3.5, "power_dbm": 43, "bandwidth_mhz": 100}
  ],
  "ues": [
    {"name": "UE_1", "prim_path": "/World/UE_1", "position": [0, 0, 1.7], "speed": 5.0}
  ]
}
EOF
fi

# Check if Kit is installed
if [ ! -f "$KIT_FILE" ]; then
    echo "❌ Kit file not found: $KIT_FILE"
    echo "Please mount the kit directory as a volume"
    exit 1
fi

# Activate Python environment if exists
if [ -f "/home/omniverse/omniverse-env/bin/activate" ]; then
    source /home/omniverse/omniverse-env/bin/activate
fi

# Launch Kit
echo ""
echo "🚀 Launching Omniverse Kit..."
echo "========================================="
echo ""

export DISPLAY=$DISPLAY
export RAN_SCENE_CONFIG=$SCENE_CONFIG

# Run Kit (keep it running)
exec python -m omni.kit_app "$KIT_FILE" "$@"
