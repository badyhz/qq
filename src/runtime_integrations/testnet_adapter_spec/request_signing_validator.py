"""Request signing architecture validator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class SigningCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def validate_architecture(content: str) -> list[SigningCheck]:
    checks = []
    checks.append(SigningCheck("mode_architecture_only", "ARCHITECTURE_ONLY" in content, "mode=ARCHITECTURE_ONLY"))
    checks.append(SigningCheck("no_real_secret", "real_secret_used=false" in content, "no real secret"))
    checks.append(SigningCheck("not_sendable", "request_sendable=false" in content, "request not sendable"))
    checks.append(SigningCheck("no_network", "network_called=false" in content, "no network call"))
    checks.append(SigningCheck("submit_not_allowed", "submit_allowed=false" in content, "submit not allowed"))
    checks.append(SigningCheck("has_canonical", "canonical" in content.lower(), "canonical format present"))
    checks.append(SigningCheck("has_timestamp", "timestamp" in content.lower(), "timestamp policy present"))
    checks.append(SigningCheck("has_nonce", "nonce" in content.lower(), "nonce policy present"))
    checks.append(SigningCheck("has_redaction", "redact" in content.lower(), "redaction requirement present"))
    checks.append(SigningCheck("has_replay", "replay" in content.lower(), "replay protection present"))
    return checks

def write_checks(checks: list[SigningCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
