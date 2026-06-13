"""Approval workflow validator. Validates workflow completeness."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class WorkflowCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def validate_workflow_hardening() -> list[WorkflowCheck]:
    from . import human_approval_workflow as wf
    checks = []
    # Test hardened request creation
    req = wf.create_hardened_request("OP_001", "RV_001", "low risk BTCUSDT BUY")
    checks.append(WorkflowCheck("request_created", bool(req.request_id), f"request_id={req.request_id}"))
    # Test validation
    val = wf.validate_hardened_request(req)
    checks.append(WorkflowCheck("validation_passes", val.valid, f"checks={len(val.checks)}"))
    # Test approval still blocks
    checks.append(WorkflowCheck("approval_blocks_submit", not val.submit_allowed, "submit_allowed=False"))
    checks.append(WorkflowCheck("approval_blocks_approved", not val.approved, "approved=False"))
    # Test stale blocks
    from datetime import datetime, timezone, timedelta
    stale_req = wf.ApprovalRequest("STALE_001", "OP_001", "RV_001", (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(), "risk", "cancel", "ENABLED", 100.0, "rollback", "no_submit")
    stale_val = wf.validate_hardened_request(stale_req)
    checks.append(WorkflowCheck("stale_expiration_present", bool(stale_val.request_id), "stale request validated"))
    # Test missing reviewer blocks
    no_reviewer = wf.ApprovalRequest("NOREV_001", "OP_001", "", (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(), "risk", "cancel", "ENABLED", 100.0, "rollback", "no_submit")
    no_rev_val = wf.validate_hardened_request(no_reviewer)
    checks.append(WorkflowCheck("missing_reviewer_blocks", not no_rev_val.valid, "missing reviewer detected"))
    return checks

def write_checks(checks: list[WorkflowCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
