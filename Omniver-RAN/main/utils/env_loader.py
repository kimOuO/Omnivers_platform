"""Environment variable loader.

Per backend_rule.md §8-3 — all env access MUST go through this module.
`os.getenv` is forbidden outside of this file.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _REPO_ROOT / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


_MISSING = object()


def _get(key: str, default: Any = _MISSING) -> str:
    val = os.getenv(key)
    if val is None or val == "":
        if default is _MISSING:
            raise RuntimeError(f"Missing required env var: {key}")
        return default
    return val


def get_str(key: str, default: str | None = None) -> str:
    return _get(key, default if default is not None else _MISSING)


def get_int(key: str, default: int | None = None) -> int:
    raw = _get(key, default if default is not None else _MISSING)
    return int(raw)


def get_bool(key: str, default: bool | None = None) -> bool:
    raw = _get(key, default if default is not None else _MISSING)
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def get_list(key: str, default: list[str] | None = None, sep: str = ",") -> list[str]:
    raw = _get(key, default if default is not None else _MISSING)
    if isinstance(raw, list):
        return raw
    return [s.strip() for s in str(raw).split(sep) if s.strip()]
