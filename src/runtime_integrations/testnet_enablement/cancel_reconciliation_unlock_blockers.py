"""Cancel and reconciliation unlock blocker matrices."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class CancelBlocker:
    blocker_id: str
    description: str
    status: str
    def to_dict(self) -> dict:
        return {"blocker_id": self.blocker_id, "description": self.description, "status": self.status}

@dataclass(frozen=True)
class ReconBlocker:
    blocker_id: str
    description: str
    status: str
    def to_dict(self) -> dict:
        return {"blocker_id": self.blocker_id, "description": self.description, "status": self.status}

CANCEL_BLOCKERS = (
    CancelBlocker("cblk_adapter", "Real cancel adapter missing", "BLOCKING"),
    CancelBlocker("cblk_idempotency", "Cancel idempotency not field-tested", "REQUIRES_FIELD_TEST"),
    CancelBlocker("cblk_terminal", "Terminal order handling not field-tested", "REQUIRES_FIELD_TEST"),
    CancelBlocker("cblk_unknown", "Unknown order handling not field-tested", "REQUIRES_FIELD_TEST"),
    CancelBlocker("cblk_audit", "Audit trail storage missing", "BLOCKING"),
    CancelBlocker("cblk_emergency", "Operator emergency cancel flow missing", "REQUIRES_FIELD_TEST"),
)

RECON_BLOCKERS = (
    ReconBlocker("rblk_balance_fetch", "Real balance fetch missing", "BLOCKING"),
    ReconBlocker("rblk_position_fetch", "Real position fetch missing", "BLOCKING"),
    ReconBlocker("rblk_staleness", "Snapshot staleness threshold not field-tested", "REQUIRES_FIELD_TEST"),
    ReconBlocker("rblk_mismatch", "Mismatch handling not field-tested", "REQUIRES_FIELD_TEST"),
    ReconBlocker("rblk_manual_override", "Manual override policy missing", "REQUIRES_HUMAN_APPROVAL"),
    ReconBlocker("rblk_audit_chain", "Audit chain external storage missing", "BLOCKING"),
)

def get_cancel_blockers() -> tuple[CancelBlocker, ...]:
    return CANCEL_BLOCKERS

def get_recon_blockers() -> tuple[ReconBlocker, ...]:
    return RECON_BLOCKERS

def write_cancel_blockers(blockers: tuple[CancelBlocker, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([b.to_dict() for b in blockers], indent=2), encoding="utf-8")

def write_recon_blockers(blockers: tuple[ReconBlocker, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([b.to_dict() for b in blockers], indent=2), encoding="utf-8")

def render_report() -> str:
    lines = ["# Cancel and Reconciliation Unlock Blockers", "",
        "## Cancel Gate", "", "**Status: CANCEL_GATE_REMAINS_LOCKED**", "", "| Blocker | Status |", "|---------|--------|"]
    for b in CANCEL_BLOCKERS:
        lines.append(f"| {b.description} | {b.status} |")
    lines.extend(["", "## Reconciliation Gate", "", "**Status: RECONCILIATION_GATE_REMAINS_LOCKED**", "", "| Blocker | Status |", "|---------|--------|"])
    for b in RECON_BLOCKERS:
        lines.append(f"| {b.description} | {b.status} |")
    lines.extend(["", "## Conclusion", "", "CANCEL_GATE_REMAINS_LOCKED", "RECONCILIATION_GATE_REMAINS_LOCKED", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
