"""Mock transport contract validator."""
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

def validate_contract(content: str) -> list[TransportCheck]:
    checks = []
    checks.append(TransportCheck("mode_mock_only", "MOCK_ONLY" in content, "mode=MOCK_ONLY"))
    checks.append(TransportCheck("no_network_client", "network_client_implemented=false" in content, "no network client"))
    checks.append(TransportCheck("no_network_call", "network_called=false" in content, "no network call"))
    checks.append(TransportCheck("submit_not_allowed", "submit_allowed=false" in content, "submit not allowed"))
    checks.append(TransportCheck("has_fixtures", "Available Fixtures" in content, "fixtures listed"))
    checks.append(TransportCheck("has_order_accepted", "order_accepted" in content, "order_accepted fixture"))
    checks.append(TransportCheck("has_order_rejected", "order_rejected" in content, "order_rejected fixture"))
    checks.append(TransportCheck("has_cancel", "cancel" in content.lower(), "cancel fixtures"))
    checks.append(TransportCheck("has_balance", "balance" in content.lower(), "balance fixture"))
    checks.append(TransportCheck("has_position", "position" in content.lower(), "position fixture"))
    return checks

def write_checks(checks: list[TransportCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
