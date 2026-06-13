"""Signature redaction. Ensures signatures are never exposed."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class RedactionCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

REDACTED_PATTERNS = ("***REDACTED***", "***STUB_REDACTED***", "***FAKE***")

def check_redaction(value: str) -> RedactionCheck:
    is_redacted = any(p in value for p in REDACTED_PATTERNS)
    return RedactionCheck("signature_redacted", is_redacted, "redacted" if is_redacted else "EXPOSED")

def check_no_real_secret(content: str) -> RedactionCheck:
    has_real = "sk-" in content or "api_key=" in content.lower()
    return RedactionCheck("no_real_secret", not has_real, "clean" if not has_real else "EXPOSED")

def write_checks(checks: list[RedactionCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
