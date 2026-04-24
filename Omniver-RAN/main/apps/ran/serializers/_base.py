"""Lightweight serializer base (no DRF). Provides validate() + errors + validated_data."""
from __future__ import annotations

from typing import Any


class Serializer:
    """Subclasses define fields via `_validate_write(data)` returning cleaned dict.
    Read side uses `to_representation(instance)`."""

    def __init__(self, data: dict[str, Any] | None = None, instance: Any = None) -> None:
        self._raw = data or {}
        self._instance = instance
        self._errors: dict[str, list[str]] = {}
        self._validated: dict[str, Any] | None = None

    # --- Write ---

    def is_valid(self) -> bool:
        self._validated = self._validate_write(self._raw)
        return not self._errors

    def _add_error(self, field: str, message: str) -> None:
        self._errors.setdefault(field, []).append(message)

    def _require(self, data: dict[str, Any], field: str, typ: type | tuple[type, ...]) -> Any:
        if field not in data:
            self._add_error(field, "required")
            return None
        val = data[field]
        if not isinstance(val, typ):
            self._add_error(field, f"must be {typ}")
        return val

    def _optional(self, data: dict[str, Any], field: str, typ: type | tuple[type, ...], default: Any = None) -> Any:
        if field not in data or data[field] is None:
            return default
        val = data[field]
        if not isinstance(val, typ):
            self._add_error(field, f"must be {typ}")
        return val

    def _validate_write(self, data: dict[str, Any]) -> dict[str, Any]:  # noqa: D401
        raise NotImplementedError

    @property
    def errors(self) -> dict[str, list[str]]:
        return self._errors

    @property
    def validated_data(self) -> dict[str, Any]:
        if self._validated is None:
            raise RuntimeError("Call is_valid() first")
        return self._validated

    # --- Read ---

    @classmethod
    def to_representation(cls, instance: Any) -> dict[str, Any]:  # noqa: D401
        raise NotImplementedError
