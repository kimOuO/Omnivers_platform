"""Reusable validation helpers. Serializer handles field-level; these are cross-cutting."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


class ValidationService:
    @staticmethod
    def parse_since(since: str | None) -> datetime:
        """Accepts `-5m`, `-1h`, `-30s`, or ISO8601."""
        if not since:
            return datetime.now(timezone.utc) - timedelta(minutes=5)
        if since.startswith("-"):
            unit = since[-1]
            n = int(since[1:-1])
            delta_map = {"s": timedelta(seconds=n), "m": timedelta(minutes=n), "h": timedelta(hours=n)}
            delta = delta_map.get(unit)
            if not delta:
                raise ValueError(f"invalid since unit: {unit!r}")
            return datetime.now(timezone.utc) - delta
        return datetime.fromisoformat(since.replace("Z", "+00:00"))

    @staticmethod
    def ensure_waypoints(waypoints: list[list[float]]) -> None:
        if not isinstance(waypoints, list) or len(waypoints) < 2:
            raise ValueError("waypoints must be a list of at least 2 points")
        for wp in waypoints:
            if not (isinstance(wp, list) and len(wp) == 3):
                raise ValueError(f"waypoint must be [x, y, z], got {wp!r}")
