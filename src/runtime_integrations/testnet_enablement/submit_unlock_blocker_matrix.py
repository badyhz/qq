"""Submit unlock blocker matrix."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class BlockerItem:
    blocker_id: str
    description: str
    status: str  # BLOCKING, REQUIRES_HUMAN_APPROVAL, REQUIRES_FIELD_TEST, REQUIRES_SECURITY_REVIEW, DESIGNED_ONLY
    def to_dict(self) -> dict:
        return {"blocker_id": self.blocker_id, "description": self.description, "status": self.status}

BLOCKERS = (
    BlockerItem("blk_cred_vault", "Real credential vault missing", "BLOCKING"),
    BlockerItem("blk_ext_adapter", "External sandbox adapter missing", "BLOCKING"),
    BlockerItem("blk_real_signing", "Real request signing missing", "BLOCKING"),
    BlockerItem("blk_approval_legal", "Human approval legal acceptance missing", "REQUIRES_HUMAN_APPROVAL"),
    BlockerItem("blk_kill_switch_test", "Kill switch field test missing", "REQUIRES_FIELD_TEST"),
    BlockerItem("blk_recon_test", "Reconciliation field test missing", "REQUIRES_FIELD_TEST"),
    BlockerItem("blk_audit_storage", "Audit log external storage missing", "BLOCKING"),
    BlockerItem("blk_emergency_drill", "Operator emergency drill missing", "REQUIRES_FIELD_TEST"),
    BlockerItem("blk_rate_limit_live", "Rate limit live behavior unknown", "REQUIRES_FIELD_TEST"),
    BlockerItem("blk_cancel_test", "Cancel safety field test missing", "REQUIRES_FIELD_TEST"),
)

def get_blockers() -> tuple[BlockerItem, ...]:
    return BLOCKERS

def write_blockers(blockers: tuple[BlockerItem, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([b.to_dict() for b in blockers], indent=2), encoding="utf-8")

def render_report(blockers: tuple[BlockerItem, ...]) -> str:
    lines = ["# Submit Unlock Blocker Matrix", "", "**Status: SUBMIT_GATE_REMAINS_LOCKED**", "**Submit: TESTNET_SUBMIT_NOT_ALLOWED**", "", "| Blocker | Status |", "|---------|--------|"]
    for b in blockers:
        lines.append(f"| {b.description} | {b.status} |")
    lines.extend(["", "## Conclusion", "", "SUBMIT_GATE_REMAINS_LOCKED", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
