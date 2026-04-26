FROM nvidia/cuda:12.6.0-base-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# System dependencies (Python 3.10 is default in Ubuntu 22.04)
RUN apt-get update && apt-get install -y \
    python3 python3-venv python3-pip \
    xvfb x11vnc novnc websockify \
    libglib2.0-0 libsm6 libxext6 libxrender1 libxrandr2 \
    libglu1-mesa \
    x11-utils x11-xserver-utils \
    && rm -rf /var/lib/apt/lists/*

# Install omniverse-kit from NVIDIA PyPI (pip, ~1.6GB, uses build cache)
RUN python3 -m venv /opt/omniverse-env \
    && /opt/omniverse-env/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/omniverse-env/bin/pip install --no-cache-dir omniverse-kit==106.0.3.138428 \
        --extra-index-url https://pypi.nvidia.com

# EULA will be auto-accepted by wrapper script (run_kit.py)

# Copy project files
WORKDIR /app
COPY extensions/ /app/extensions/
COPY assets/ /app/assets/
COPY kit/ran_server.kit /app/kit/ran_server.kit
COPY kit/run_kit.py /app/kit/run_kit.py
COPY scene_config.json /app/scene_config.json
RUN chmod +x /app/kit/run_kit.py

# Fix Kit config: convert host extension path to container path (volume mount)
# scene_config.json uses host absolute paths, accessible via volume mount
RUN sed -i 's|/home/mitlab/XAPP_DT/Omnivers_platform/extensions|/app/extensions|g' \
        /app/kit/ran_server.kit

COPY kit/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    sed -i 's/:88/:99/g' /entrypoint.sh

# Expose ports: Kit API + WebSocket + VNC + noVNC
EXPOSE 8080 8081 5900 6080

ENTRYPOINT ["/entrypoint.sh"]
