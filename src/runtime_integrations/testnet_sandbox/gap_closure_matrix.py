"""Gap closure matrix. Tracks closure status of testnet sandbox gaps."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class GapItem:
    gap_id: str
    category: str
    description: str
    status: str  # DESIGNED, STUB_ONLY, SIMULATED_ONLY, MISSING, BLOCKED, REQUIRES_HUMAN_APPROVAL
    blocking: bool
    def to_dict(self) -> dict:
        return {"gap_id": self.gap_id, "category": self.category, "description": self.description, "status": self.status, "blocking": self.blocking}

GAPS = (
    GapItem("gap_adapter_interface", "adapter interface", "Testnet sandbox adapter interface designed", "DESIGNED", False),
    GapItem("gap_simulated_adapter", "adapter interface", "Simulated exchange adapter implemented", "SIMULATED_ONLY", False),
    GapItem("gap_credential_vault", "credential vault", "Credential vault stub only, no real keys", "STUB_ONLY", True),
    GapItem("gap_human_approval", "human approval", "Human approval gate implemented, default DENY", "DESIGNED", True),
    GapItem("gap_risk_controls", "risk controls", "Sandbox risk controls implemented", "DESIGNED", False),
    GapItem("gap_kill_switch", "kill switch", "Kill switch implemented, default BLOCKING", "DESIGNED", True),
    GapItem("gap_cancel_safety", "cancel safety", "Order cancel safety simulated only", "SIMULATED_ONLY", True),
    GapItem("gap_position_recon", "position reconciliation", "Position reconciliation not implemented", "MISSING", True),
    GapItem("gap_balance_recon", "balance reconciliation", "Balance reconciliation not implemented", "MISSING", True),
    GapItem("gap_rate_limits", "rate limits", "Rate limit handling not implemented", "MISSING", True),
    GapItem("gap_network_failure", "network failure handling", "Network failure handling not implemented", "MISSING", True),
    GapItem("gap_audit_logging", "audit logging", "Audit logging for sandbox operations not implemented", "MISSING", False),
    GapItem("gap_operator_emergency", "operator emergency procedure", "Operator emergency procedure not implemented", "MISSING", True),
)

def get_gaps() -> tuple[GapItem, ...]:
    return GAPS

def render_closure_matrix() -> str:
    lines = ["# Testnet Sandbox Gap Closure Matrix", "", "**Status: TESTNET_SANDBOX_NOT_READY_FOR_SUBMIT**", "", "| Gap | Category | Status | Blocking |", "|-----|----------|--------|----------|"]
    for g in GAPS:
        lines.append(f"| {g.description} | {g.category} | {g.status} | {g.blocking} |")
    lines.extend(["", "## Conclusion", "", "TESTNET_SANDBOX_NOT_READY_FOR_SUBMIT", ""])
    return "\n".join(lines)

def render_next_stage_blockers() -> str:
    blocking = [g for g in GAPS if g.blocking and g.status in ("MISSING", "BLOCKED")]
    lines = ["# Testnet Sandbox Next Stage Blockers", "", "The following gaps are blocking and must be resolved before testnet submit:", ""]
    for g in blocking:
        lines.append(f"- **{g.gap_id}** ({g.category}): {g.description} — {g.status}")
    lines.extend(["", "## Required for T110001-T125000", "", "- Credential vault real implementation review", "- Exchange sandbox adapter stub", "- Cancel safety implementation", "- Position reconciliation design", "- Balance reconciliation design", "- Rate limit handling", "- Network failure handling", "- Operator emergency procedure", ""])
    return "\n".join(lines)

def write_gaps(gaps: tuple[GapItem, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([g.to_dict() for g in gaps], indent=2), encoding="utf-8")
