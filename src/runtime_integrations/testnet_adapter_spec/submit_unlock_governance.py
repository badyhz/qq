"""Submit unlock governance draft."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class GovernanceItem:
    item_id: str
    title: str
    content: str
    required: bool
    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "title": self.title, "content": self.content, "required": self.required}

ITEMS = (
    GovernanceItem("required_approvals", "Required Approvals", "Minimum 3 independent human approvals: operator, reviewer, security. Each must be authenticated.", True),
    GovernanceItem("operator_ack", "Operator Acknowledgement", "Operator must acknowledge risks, read-only constraints, and emergency procedures.", True),
    GovernanceItem("reviewer_ack", "Reviewer Acknowledgement", "Reviewer must independently verify all safety controls are in place.", True),
    GovernanceItem("security_review", "Security Review", "Security reviewer must verify credential vault, access control, and audit logging.", True),
    GovernanceItem("vault_approval", "Credential Vault Approval", "Credential vault must be reviewed and approved before submit unlock.", True),
    GovernanceItem("adapter_review", "Adapter Implementation Review", "External adapter implementation must pass code review and safety scan.", True),
    GovernanceItem("dry_run_evidence", "Dry-Run Evidence", "Complete dry-run evidence showing all safety controls work as designed.", True),
    GovernanceItem("field_test_scope", "Field-Test Scope", "Defined scope for field test: symbols, notional caps, duration, rollback plan.", True),
    GovernanceItem("max_notional", "Max Notional Cap", "Per-order notional cap must be set. Default: 100 USDT. Requires approval to increase.", True),
    GovernanceItem("symbol_allowlist", "Symbol Allowlist", "Only approved symbols. Default: empty. Each symbol requires individual approval.", True),
    GovernanceItem("kill_switch_proof", "Kill Switch Proof", "Kill switch must be tested and verified to block all submits.", True),
    GovernanceItem("rollback_proof", "Rollback Proof", "Rollback procedure must be tested and verified.", True),
    GovernanceItem("audit_retention", "Audit Retention Proof", "Audit log retention must be verified: tamper-evident, external storage, 90-day retention.", True),
    GovernanceItem("unlock_expiration", "Submit Unlock Expiration", "Submit unlock must have an expiration time. Default: 24 hours. Requires re-approval to extend.", True),
    GovernanceItem("unlock_revocation", "Submit Unlock Revocation", "Any approver can revoke submit unlock immediately. Revocation logged.", True),
)

def get_items() -> tuple[GovernanceItem, ...]:
    return ITEMS

def write_governance(items: tuple[GovernanceItem, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([i.to_dict() for i in items], indent=2), encoding="utf-8")

def render_report(items: tuple[GovernanceItem, ...]) -> str:
    lines = ["# Submit Unlock Governance Draft", "",
        "**governance_mode=DRAFT_ONLY**",
        "**submit_gate_state=LOCKED**",
        "**testnet_submit_allowed=false**",
        "**real_submit_allowed=false**", ""]
    for i in items:
        lines.extend([f"## {i.title}", "", i.content, ""])
    lines.extend(["## Conclusion", "", "SUBMIT_UNLOCK_GOVERNANCE_DRAFT_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
