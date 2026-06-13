"""Human approval workflow. Hardened approval with required fields."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

@dataclass(frozen=True)
class ApprovalRequest:
    request_id: str
    operator_id: str
    reviewer_id: str
    expires_at: str
    risk_summary: str
    cancel_plan: str
    kill_switch_state: str
    max_notional: float
    rollback_plan: str
    no_submit_declaration: str
    def to_dict(self) -> dict:
        return {"request_id": self.request_id, "operator_id": self.operator_id, "reviewer_id": self.reviewer_id, "expires_at": self.expires_at, "risk_summary": self.risk_summary, "cancel_plan": self.cancel_plan, "kill_switch_state": self.kill_switch_state, "max_notional": self.max_notional, "rollback_plan": self.rollback_plan, "no_submit_declaration": self.no_submit_declaration}

@dataclass(frozen=True)
class ApprovalValidation:
    request_id: str
    valid: bool
    checks: tuple[str, ...]
    approved: bool
    submit_allowed: bool
    def to_dict(self) -> dict:
        return {"request_id": self.request_id, "valid": self.valid, "checks": list(self.checks), "approved": self.approved, "submit_allowed": self.submit_allowed}

def create_hardened_request(operator_id: str, reviewer_id: str, risk_summary: str) -> ApprovalRequest:
    now = datetime.now(timezone.utc)
    return ApprovalRequest(
        request_id=f"HAPR_{uuid.uuid4().hex[:12]}",
        operator_id=operator_id, reviewer_id=reviewer_id,
        expires_at=(now + timedelta(hours=1)).isoformat(),
        risk_summary=risk_summary, cancel_plan="cancel all open simulated orders",
        kill_switch_state="ENABLED_BLOCKING", max_notional=1000.0,
        rollback_plan="restore to last known good state",
        no_submit_declaration="I confirm no real submit will occur",
    )

def validate_hardened_request(req: ApprovalRequest) -> ApprovalValidation:
    checks = []
    ok = True
    if not req.request_id:
        checks.append("REQUEST_ID_REQUIRED"); ok = False
    else:
        checks.append("request_id_present")
    if not req.operator_id:
        checks.append("OPERATOR_ID_REQUIRED"); ok = False
    else:
        checks.append("operator_id_present")
    if not req.reviewer_id:
        checks.append("REVIEWER_ID_REQUIRED"); ok = False
    else:
        checks.append("reviewer_id_present")
    if not req.expires_at:
        checks.append("EXPIRATION_REQUIRED"); ok = False
    else:
        checks.append("expiration_present")
    if not req.risk_summary:
        checks.append("RISK_SUMMARY_REQUIRED"); ok = False
    else:
        checks.append("risk_summary_present")
    if not req.cancel_plan:
        checks.append("CANCEL_PLAN_REQUIRED"); ok = False
    else:
        checks.append("cancel_plan_present")
    if not req.kill_switch_state:
        checks.append("KILL_SWITCH_STATE_REQUIRED"); ok = False
    else:
        checks.append("kill_switch_state_present")
    if not req.rollback_plan:
        checks.append("ROLLBACK_PLAN_REQUIRED"); ok = False
    else:
        checks.append("rollback_plan_present")
    if not req.no_submit_declaration:
        checks.append("NO_SUBMIT_DECLARATION_REQUIRED"); ok = False
    else:
        checks.append("no_submit_declaration_present")
    return ApprovalValidation(req.request_id, ok, tuple(checks), False, False)

def write_validation(val: ApprovalValidation, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(val.to_dict(), indent=2), encoding="utf-8")
