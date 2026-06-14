"""Cancel and reconciliation governance draft."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class CancelGovernanceItem:
    item_id: str
    title: str
    content: str
    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "title": self.title, "content": self.content}

@dataclass(frozen=True)
class ReconGovernanceItem:
    item_id: str
    title: str
    content: str
    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "title": self.title, "content": self.content}

CANCEL_ITEMS = (
    CancelGovernanceItem("idempotency", "Cancel Idempotency Proof", "Cancel must be idempotent. Duplicate cancel returns success without error."),
    CancelGovernanceItem("unknown_order", "Unknown Order Policy", "Cancel of unknown order returns success (already cancelled or never existed)."),
    CancelGovernanceItem("terminal_order", "Terminal Order Policy", "Cancel of terminal order (filled, cancelled, expired) returns success."),
    CancelGovernanceItem("duplicate_cancel", "Duplicate Cancel Policy", "Duplicate cancel within 60s returns cached result."),
    CancelGovernanceItem("emergency_cancel", "Emergency Cancel Procedure", "Operator can cancel all open orders immediately. Requires confirmation."),
    CancelGovernanceItem("cancel_audit", "Cancel Audit Log Proof", "Every cancel attempt logged: order_id, result, timestamp, operator."),
    CancelGovernanceItem("manual_override", "Manual Cancel Override Policy", "Operator can override cancel failures. Override logged and reviewed."),
)

RECON_ITEMS = (
    ReconGovernanceItem("balance_snapshot", "Balance Snapshot Proof", "Balance snapshot taken before and after each reconciliation cycle."),
    ReconGovernanceItem("position_snapshot", "Position Snapshot Proof", "Position snapshot taken before and after each reconciliation cycle."),
    ReconGovernanceItem("staleness", "Staleness Threshold", "Snapshots older than 30s considered stale. Stale snapshots trigger warning."),
    ReconGovernanceItem("mismatch", "Mismatch Resolution Policy", "Mismatch detected: log warning, hold new orders, notify operator."),
    ReconGovernanceItem("manual_override", "Manual Override Policy", "Operator can override mismatch. Override logged and reviewed."),
    ReconGovernanceItem("audit_chain", "Audit Chain Proof", "Reconciliation events in tamper-evident audit chain."),
    ReconGovernanceItem("operator_review", "Operator Review Policy", "Operator must review reconciliation report before next trading cycle."),
)

def get_cancel_items() -> tuple[CancelGovernanceItem, ...]:
    return CANCEL_ITEMS

def get_recon_items() -> tuple[ReconGovernanceItem, ...]:
    return RECON_ITEMS

def write_governance(cancel_items: tuple[CancelGovernanceItem, ...], recon_items: tuple[ReconGovernanceItem, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "cancel_governance": [i.to_dict() for i in cancel_items],
        "reconciliation_governance": [i.to_dict() for i in recon_items],
    }
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")

def render_report(cancel_items: tuple[CancelGovernanceItem, ...], recon_items: tuple[ReconGovernanceItem, ...]) -> str:
    lines = ["# Cancel and Reconciliation Governance Draft", "",
        "**cancel_gate_state=LOCKED**",
        "**reconciliation_gate_state=LOCKED**",
        "**testnet_cancel_allowed=false**",
        "**testnet_submit_allowed=false**", ""]
    lines.extend(["## Cancel Governance", ""])
    for i in cancel_items:
        lines.extend([f"### {i.title}", "", i.content, ""])
    lines.extend(["## Reconciliation Governance", ""])
    for i in recon_items:
        lines.extend([f"### {i.title}", "", i.content, ""])
    lines.extend(["## Conclusion", "", "CANCEL_RECONCILIATION_GOVERNANCE_DRAFT_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
