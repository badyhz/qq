"""Field-test acceptance criteria validator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class FieldTestCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def validate_criteria(content: str) -> list[FieldTestCheck]:
    checks = []
    checks.append(FieldTestCheck("mode_criteria_only", "CRITERIA_ONLY" in content, "mode=CRITERIA_ONLY"))
    checks.append(FieldTestCheck("not_executed", "field_test_executed=false" in content, "field test not executed"))
    checks.append(FieldTestCheck("submit_not_allowed", "submit_allowed=false" in content, "submit not allowed"))
    checks.append(FieldTestCheck("has_dry_run_parity", "dry-run" in content.lower() or "dry_run" in content.lower(), "dry-run parity present"))
    checks.append(FieldTestCheck("has_vault_approval", "vault" in content.lower() and "approved" in content.lower(), "vault approval present"))
    checks.append(FieldTestCheck("has_kill_switch", "kill switch" in content.lower(), "kill switch present"))
    checks.append(FieldTestCheck("has_rollback", "rollback" in content.lower(), "rollback present"))
    checks.append(FieldTestCheck("has_operator", "operator" in content.lower(), "operator requirement present"))
    checks.append(FieldTestCheck("has_audit", "audit" in content.lower(), "audit present"))
    checks.append(FieldTestCheck("has_notional_cap", "notional" in content.lower(), "notional cap present"))
    return checks

def write_checks(checks: list[FieldTestCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
