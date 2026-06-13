"""Final blocker matrix. Shows all remaining blockers before real testnet submit."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class BlockerItem:
    blocker_id: str
    category: str
    description: str
    status: str  # BLOCKING, DESIGNED_ONLY, SIMULATED_ONLY, REQUIRES_HUMAN_REVIEW, REQUIRES_SEPARATE_APPROVAL
    def to_dict(self) -> dict:
        return {"blocker_id": self.blocker_id, "category": self.category, "description": self.description, "status": self.status}

BLOCKERS = (
    BlockerItem("blk_cred_vault", "credential", "Real credential vault not implemented", "BLOCKING"),
    BlockerItem("blk_exchange_adapter", "adapter", "Real exchange adapter not implemented", "BLOCKING"),
    BlockerItem("blk_request_signing", "signing", "Real request signing not implemented", "BLOCKING"),
    BlockerItem("blk_network_transport", "transport", "Real network transport not implemented", "BLOCKING"),
    BlockerItem("blk_testnet_submit", "submit", "Real testnet submit not implemented", "BLOCKING"),
    BlockerItem("blk_cancel_api", "cancel", "Real cancel API not implemented", "BLOCKING"),
    BlockerItem("blk_position_recon", "reconciliation", "Position reconciliation only simulated", "SIMULATED_ONLY"),
    BlockerItem("blk_balance_recon", "reconciliation", "Balance reconciliation only simulated", "SIMULATED_ONLY"),
    BlockerItem("blk_rate_limit", "resilience", "Rate limit handling only simulated", "SIMULATED_ONLY"),
    BlockerItem("blk_approval_legal", "governance", "Operator approval not legally binding", "REQUIRES_HUMAN_REVIEW"),
    BlockerItem("blk_emergency_test", "operations", "Emergency procedure not field-tested", "REQUIRES_HUMAN_REVIEW"),
    BlockerItem("blk_audit_storage", "audit", "Audit log not externally stored", "DESIGNED_ONLY"),
)

def get_blockers() -> tuple[BlockerItem, ...]:
    return BLOCKERS

def render_matrix() -> str:
    lines = ["# Sandbox Final Blocker Matrix", "", "**Status: TESTNET_SANDBOX_FINAL_GATE_REVIEW_READY**", "**Submit: TESTNET_SUBMIT_NOT_ALLOWED**", "", "| Blocker | Category | Status |", "|---------|----------|--------|"]
    for b in BLOCKERS:
        lines.append(f"| {b.description} | {b.category} | {b.status} |")
    lines.extend(["", "## Conclusion", "", "TESTNET_SANDBOX_FINAL_GATE_REVIEW_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)

def render_next_stage_blockers() -> str:
    blocking = [b for b in BLOCKERS if b.status == "BLOCKING"]
    lines = ["# Sandbox Final Next Stage Blockers", "", "The following must be resolved before testnet submit:", ""]
    for b in blocking:
        lines.append(f"- **{b.blocker_id}** ({b.category}): {b.description}")
    lines.extend(["", "## Required for T140001-T155000", "", "- Real credential vault implementation", "- Real exchange adapter integration", "- Real request signing", "- Real network transport", "- Real testnet submit implementation", "- Real cancel API", ""])
    return "\n".join(lines)

def write_blockers(blockers: tuple[BlockerItem, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([b.to_dict() for b in blockers], indent=2), encoding="utf-8")
