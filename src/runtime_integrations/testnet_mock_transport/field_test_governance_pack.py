"""Field-test governance pack."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class GovernanceChecklist:
    checklist_id: str
    category: str
    title: str
    content: str
    required: bool
    def to_dict(self) -> dict:
        return {"checklist_id": self.checklist_id, "category": self.category, "title": self.title, "content": self.content, "required": self.required}

CHECKLISTS = (
    GovernanceChecklist("ft_scope", "scope", "Field-Test Scope", "Define allowed symbols, max notional, duration, and rollback plan before field test.", True),
    GovernanceChecklist("ft_approval", "approval", "Required Human Approval Checklist", "Operator ack, reviewer ack, security review, risk approval — all required before field test.", True),
    GovernanceChecklist("ft_credential_review", "credential", "Required Credential Review Checklist", "Credential vault approved, keys rotated, permissions verified, no withdraw permission.", True),
    GovernanceChecklist("ft_exchange_permission", "permission", "Required Exchange Permission Checklist", "IP allowlist, read/trade permissions, no withdraw, sub-account isolation.", True),
    GovernanceChecklist("ft_symbol_allowlist", "symbols", "Allowed Testnet Symbols Checklist", "Default: empty. Each symbol requires individual approval. BTCUSDT, ETHUSDT suggested.", True),
    GovernanceChecklist("ft_notional_cap", "limits", "Max Notional Placeholder Policy", "Default: 100 USDT per order. Requires explicit approval to increase.", True),
    GovernanceChecklist("ft_kill_switch", "safety", "Kill Switch Precondition", "Kill switch must be armed and tested before field test begins.", True),
    GovernanceChecklist("ft_rollback", "safety", "Rollback Procedure", "Point-in-time restore, artifact preservation, audit log continuity. Must be rehearsed.", True),
    GovernanceChecklist("ft_audit", "audit", "Audit Log Requirement", "Tamper-evident chain, external storage, 90-day retention, export capability.", True),
    GovernanceChecklist("ft_evidence", "evidence", "Evidence Bundle Requirement", "All test results, approvals, and audit logs bundled for post-test review.", True),
    GovernanceChecklist("ft_max_daily", "limits", "Daily Order Cap", "Default: 10 orders per day during field test. Requires approval to increase.", True),
    GovernanceChecklist("ft_operator_present", "safety", "Operator Present Requirement", "Operator must be present during entire field test duration.", True),
)

def get_checklists() -> tuple[GovernanceChecklist, ...]:
    return CHECKLISTS

def write_governance(checklists: tuple[GovernanceChecklist, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checklists], indent=2), encoding="utf-8")

def render_report(checklists: tuple[GovernanceChecklist, ...]) -> str:
    lines = ["# Field-Test Governance Pack", "",
        "**governance_mode=PACK_ONLY**",
        "**field_test_executed=false**",
        "**submit_allowed=false**", ""]
    lines.append("| Category | Title | Required |")
    lines.append("|----------|-------|----------|")
    for c in checklists:
        lines.append(f"| {c.category} | {c.title} | {c.required} |")
    lines.extend(["", "## Conclusion", "", "FIELD_TEST_GOVERNANCE_PACK_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
