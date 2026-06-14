"""Network transport architecture validator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class TransportCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def validate_architecture(content: str) -> list[TransportCheck]:
    checks = []
    checks.append(TransportCheck("mode_architecture_only", "ARCHITECTURE_ONLY" in content, "mode=ARCHITECTURE_ONLY"))
    checks.append(TransportCheck("no_network_client", "network_client_implemented=false" in content, "no network client"))
    checks.append(TransportCheck("no_network_call", "network_called=false" in content, "no network call"))
    checks.append(TransportCheck("submit_not_allowed", "submit_allowed=false" in content, "submit not allowed"))
    checks.append(TransportCheck("has_timeout", "timeout" in content.lower(), "timeout policy present"))
    checks.append(TransportCheck("has_retry", "retry" in content.lower(), "retry policy present"))
    checks.append(TransportCheck("has_rate_limit", "rate limit" in content.lower(), "rate limit policy present"))
    checks.append(TransportCheck("has_circuit_breaker", "circuit breaker" in content.lower(), "circuit breaker present"))
    checks.append(TransportCheck("has_idempotency", "idempotency" in content.lower(), "idempotency present"))
    checks.append(TransportCheck("has_audit", "audit" in content.lower(), "audit event present"))
    return checks

def write_checks(checks: list[TransportCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
