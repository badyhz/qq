"""Read-only hook sanitizer — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

SECRET_PATTERNS = ["api_key", "secret", "password", "token", "credential", "private_key"]


@dataclass(frozen=True)
class SanitizedPayload:
    original_keys: List[str]
    sanitized_keys: List[str]
    redacted_fields: List[str]
    payload: Dict[str, Any]


def _is_secret_key(key: str) -> bool:
    lower = key.lower()
    return any(pattern in lower for pattern in SECRET_PATTERNS)


def sanitize_payload(payload: Dict[str, Any]) -> SanitizedPayload:
    original_keys = sorted(payload.keys())
    redacted: List[str] = []
    sanitized: Dict[str, Any] = {}
    for key, value in payload.items():
        if _is_secret_key(key):
            redacted.append(key)
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    sanitized_keys = sorted(sanitized.keys())
    return SanitizedPayload(
        original_keys=original_keys,
        sanitized_keys=sanitized_keys,
        redacted_fields=sorted(redacted),
        payload=sanitized,
    )


def sanitized_payload_to_dict(sp: SanitizedPayload) -> dict:
    return {
        "original_keys": list(sp.original_keys),
        "sanitized_keys": list(sp.sanitized_keys),
        "redacted_fields": list(sp.redacted_fields),
        "payload": dict(sp.payload),
    }
