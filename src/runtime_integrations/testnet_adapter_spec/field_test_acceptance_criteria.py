"""Field-test acceptance criteria."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class Criterion:
    criterion_id: str
    title: str
    content: str
    required: bool
    def to_dict(self) -> dict:
        return {"criterion_id": self.criterion_id, "title": self.title, "content": self.content, "required": self.required}

CRITERIA = (
    Criterion("dry_run_parity", "Dry-Run Parity Before Field Test", "All dry-run tests must pass before field test begins.", True),
    Criterion("vault_approved", "Credential Vault Approved", "Credential vault must be reviewed and approved.", True),
    Criterion("signing_reviewed", "Request Signing Reviewed", "Request signing implementation must be reviewed.", True),
    Criterion("transport_reviewed", "Network Transport Reviewed", "Network transport implementation must be reviewed.", True),
    Criterion("submit_unlock", "Submit Gate Temporary Unlock Approval", "Explicit approval for temporary submit unlock during field test.", True),
    Criterion("cancel_unlock", "Cancel Gate Temporary Unlock Approval", "Explicit approval for temporary cancel unlock during field test.", True),
    Criterion("recon_unlock", "Reconciliation Gate Temporary Unlock Approval", "Explicit approval for temporary reconciliation unlock during field test.", True),
    Criterion("symbol_allowlist", "Symbol Allowlist", "Only approved symbols allowed during field test.", True),
    Criterion("notional_cap", "Notional Cap", "Per-order notional cap set and enforced.", True),
    Criterion("daily_cap", "Daily Order Cap", "Daily order cap set and enforced.", True),
    Criterion("operator_present", "Manual Operator Present", "Operator must be present during entire field test.", True),
    Criterion("kill_switch_armed", "Kill Switch Armed", "Kill switch must be armed and tested.", True),
    Criterion("audit_backup", "Audit Log External Backup", "Audit log backed up to external storage before field test.", True),
    Criterion("rollback_rehearsal", "Rollback Rehearsal", "Rollback procedure rehearsed before field test.", True),
    Criterion("post_review", "Post-Test Review", "Post-test review required before next phase.", True),
)

def get_criteria() -> tuple[Criterion, ...]:
    return CRITERIA

def write_criteria(criteria: tuple[Criterion, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in criteria], indent=2), encoding="utf-8")

def render_report(criteria: tuple[Criterion, ...]) -> str:
    lines = ["# Field-Test Acceptance Criteria", "",
        "**field_test_mode=CRITERIA_ONLY**",
        "**field_test_executed=false**",
        "**submit_allowed=false**", ""]
    for c in criteria:
        lines.extend([f"## {c.title}", "", c.content, ""])
    lines.extend(["## Conclusion", "", "FIELD_TEST_ACCEPTANCE_CRITERIA_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
