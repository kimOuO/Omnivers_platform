"""Shared Actor helpers: parse JSON body, decorator composition."""
from __future__ import annotations

import json
from typing import Any

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from main.utils.response import error_response


def parse_body(request) -> tuple[dict[str, Any] | None, Any]:
    """Returns (data, error_response) — exactly one is None."""
    if not request.body:
        return {}, None
    try:
        return json.loads(request.body), None
    except json.JSONDecodeError as e:
        return None, error_response("Invalid JSON body", {"detail": str(e)}, 400)


post_only = require_http_methods(["POST"])


def actor(fn):
    """Compose @csrf_exempt + @require_http_methods(['POST'])."""
    return csrf_exempt(post_only(fn))
