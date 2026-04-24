"""Standardized JSON response helpers.

Per backend_rule.md §13-2 — Actors MUST use these, not JsonResponse directly.
"""
from __future__ import annotations

from typing import Any
from django.http import JsonResponse


def success_response(
    data: Any = None,
    message: str = "OK",
    status: int = 200,
) -> JsonResponse:
    return JsonResponse(
        {"success": True, "message": message, "data": data},
        status=status,
    )


def error_response(
    message: str,
    errors: Any = None,
    status: int = 400,
    code: str | None = None,
) -> JsonResponse:
    body: dict[str, Any] = {"success": False, "message": message}
    if errors is not None:
        body["errors"] = errors
    if code is not None:
        body["code"] = code
    return JsonResponse(body, status=status)
