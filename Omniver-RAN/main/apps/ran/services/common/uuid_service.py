"""UUID generation — deterministic per (entity_type, key) or fully random."""
from __future__ import annotations

import hashlib
import uuid


class UUIDService:
    @staticmethod
    def generate_uuid(entity_type: str, key: str | None = None) -> str:
        """If key given, hash-based deterministic UUID; otherwise random UUID4."""
        if key is None:
            return str(uuid.uuid4())
        digest = hashlib.sha1(f"{entity_type}:{key}".encode()).hexdigest()[:32]
        return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:]}"

    @staticmethod
    def random_uuid() -> str:
        return str(uuid.uuid4())
