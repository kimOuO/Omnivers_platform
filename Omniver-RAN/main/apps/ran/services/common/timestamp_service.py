"""Timestamp helpers."""
from __future__ import annotations

from datetime import datetime, timezone


class TimestampService:
    @staticmethod
    def get_current_timestamp() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def parse_iso(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
