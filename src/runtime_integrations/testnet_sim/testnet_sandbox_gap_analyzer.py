"""Testnet sandbox gap analyzer. Documents what's missing before testnet submit."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class GapItem:
    gap_id: str
    category: str
    description: str
    status: str  # MISSING, PARTIAL, DOCUMENTED
    blocking: bool
    def to_dict(self) -> dict:
        return {"gap_id": self.gap_id, "category": self.category, "description": self.description, "status": self.status, "blocking": self.blocking}

GAPS = (
    GapItem("gap_exchange_adapter", "exchange", "Binance testnet API adapter not implemented", "MISSING", True),
    GapItem("gap_credential_vault", "security", "Secure credential vault not implemented", "MISSING", True),
    GapItem("gap_submit_approval", "workflow", "Submit approval workflow not implemented", "MISSING", True),
    GapItem("gap_order_cancel", "safety", "Order cancel safety mechanism not implemented", "MISSING", True),
    GapItem("gap_position_recon", "reconciliation", "Position reconciliation not implemented", "MISSING", True),
    GapItem("gap_balance_recon", "reconciliation", "Balance reconciliation not implemented", "MISSING", True),
    GapItem("gap_rate_limit", "resilience", "Sandbox rate limit handling not implemented", "MISSING", True),
    GapItem("gap_network_failure", "resilience", "Sandbox network failure handling not implemented", "MISSING", True),
    GapItem("gap_kill_switch", "safety", "Manual kill switch not implemented", "MISSING", True),
    GapItem("gap_audit_logging", "observability", "Audit logging for testnet operations not implemented", "MISSING", True),
    GapItem("gap_human_approval", "governance", "Human approval gate not implemented", "MISSING", True),
)

def get_gaps() -> tuple[GapItem, ...]:
    return GAPS

def render_gap_report_markdown() -> str:
    lines = ["# Testnet Sandbox Readiness Gap Report", "", "**Status: TESTNET_SANDBOX_NOT_READY_FOR_SUBMIT**", "", "| Gap | Category | Status | Blocking |", "|-----|----------|--------|----------|"]
    for g in GAPS:
        lines.append(f"| {g.description} | {g.category} | {g.status} | {g.blocking} |")
    lines.extend(["", "## Conclusion", "", "TESTNET_SANDBOX_NOT_READY_FOR_SUBMIT", "TESTNET_SANDBOX_GAP_DOCUMENTED", ""])
    return "\n".join(lines)

def render_approval_checklist_markdown() -> str:
    lines = ["# Testnet Sandbox Human Approval Checklist", "", "Before any testnet submit:", ""]
    for g in GAPS:
        lines.append(f"- [ ] {g.description}")
    lines.extend(["", "- [ ] Human signs off on testnet sandbox use case", "- [ ] Risk engine validated", "- [ ] Rollback plan documented", ""])
    return "\n".join(lines)

def write_gaps(gaps: tuple[GapItem, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([g.to_dict() for g in gaps], indent=2), encoding="utf-8")
