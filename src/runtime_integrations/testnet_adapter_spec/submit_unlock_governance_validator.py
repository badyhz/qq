"""Submit unlock governance validator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class GovernanceCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def validate_governance(content: str) -> list[GovernanceCheck]:
    checks = []
    checks.append(GovernanceCheck("mode_draft_only", "DRAFT_ONLY" in content, "mode=DRAFT_ONLY"))
    checks.append(GovernanceCheck("gate_locked", "submit_gate_state=LOCKED" in content, "gate remains locked"))
    checks.append(GovernanceCheck("testnet_not_allowed", "testnet_submit_allowed=false" in content, "testnet submit not allowed"))
    checks.append(GovernanceCheck("real_not_allowed", "real_submit_allowed=false" in content, "real submit not allowed"))
    checks.append(GovernanceCheck("has_approvals", "approval" in content.lower(), "approval requirements present"))
    checks.append(GovernanceCheck("has_kill_switch", "kill switch" in content.lower(), "kill switch present"))
    checks.append(GovernanceCheck("has_rollback", "rollback" in content.lower(), "rollback present"))
    checks.append(GovernanceCheck("has_audit", "audit" in content.lower(), "audit present"))
    checks.append(GovernanceCheck("has_expiration", "expiration" in content.lower(), "expiration present"))
    checks.append(GovernanceCheck("has_revocation", "revocation" in content.lower(), "revocation present"))
    return checks

def write_checks(checks: list[GovernanceCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
