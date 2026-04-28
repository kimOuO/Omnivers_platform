"""Shared configuration file location definitions.

Used by both API extension and Scene Builder to ensure consistency.
Only ONE list, used for both writing and reading.
"""
import os
from typing import List, Tuple


def get_config_candidates() -> List[Tuple[str, str]]:
    """
    Get list of candidate config file locations in priority order.

    Both API Extension (writing) and Scene Builder (reading) use this same list.
    This ensures they always stay in sync.

    Returns:
        List of (label, path) tuples.
        When writing: tries each location in order, uses first success.
        When reading: tries each location in order, uses first that exists.
    """
    candidates = []

    # 1️⃣ Primary: Runtime config in home directory
    # API /scene/config endpoint writes here first (highest priority)
    candidates.append((
        "API runtime (home)",
        os.path.expanduser("~/.omniverse_runtime_config.json")
    ))

    # 2️⃣ Fallback 1: /tmp (if home directory is read-only)
    candidates.append((
        "API runtime (/tmp)",
        "/tmp/.omniverse_runtime_config.json"
    ))

    # 3️⃣ Fallback 2: Environment variable (if set by user/operator)
    # Allows deployment flexibility: export RAN_SCENE_CONFIG=/custom/path/config.json
    env_path = os.environ.get("RAN_SCENE_CONFIG")
    if env_path:
        candidates.append((
            "env RAN_SCENE_CONFIG",
            os.path.expanduser(env_path)
        ))

    # 4️⃣ Fallback 3: Docker container path
    # For containerized deployments where config is mounted at /app
    candidates.append((
        "Docker container",
        "/app/scene_config.json"
    ))

    # 5️⃣ Fallback 4: Project directory (relative to home)
    # Static scene config in the project repo
    candidates.append((
        "Project directory",
        os.path.expanduser("~/XAPP_DT/Omnivers_platform/scene_config.json")
    ))

    # 6️⃣ Fallback 5: Legacy location
    # For backward compatibility with older deployments
    candidates.append((
        "Legacy omniverse",
        os.path.expanduser("~/omniverse/scene_config.json")
    ))

    return candidates
