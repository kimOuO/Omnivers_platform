"""Logger factory. Safe for copy into any Django project."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from main.utils.env_loader import get_str

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG_DIR = _REPO_ROOT / "logs"

_LEVEL = get_str("LOG_LEVEL", "INFO").upper()
_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class _SafeRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that swallows disk-full / permission errors instead
    of crashing the request thread. Once a write fails, we stop trying."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._disabled = False

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        if self._disabled:
            return
        try:
            super().emit(record)
        except (OSError, ValueError):
            # Disk full, permission, closed stream... stop writing to file.
            self._disabled = True
            try:
                self.close()
            except Exception:  # noqa: BLE001
                pass

    def shouldRollover(self, record: logging.LogRecord) -> bool:  # noqa: N802
        if self._disabled:
            return False
        try:
            return super().shouldRollover(record)
        except OSError:
            self._disabled = True
            return False


def _build_file_handler() -> logging.Handler | None:
    """Best-effort file handler; returns None if logs/ can't be prepared."""
    try:
        _LOG_DIR.mkdir(exist_ok=True)
        h = _SafeRotatingFileHandler(
            _LOG_DIR / "omniver_ran.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        h.setFormatter(logging.Formatter(_FORMAT))
        return h
    except (OSError, PermissionError) as e:
        print(f"[logger] file handler disabled: {e}", file=sys.stderr)
        return None


_file_handler = _build_file_handler()

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter(_FORMAT))


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(_LEVEL)
        if _file_handler is not None:
            logger.addHandler(_file_handler)
        logger.addHandler(_console_handler)
        logger.propagate = False
    return logger
