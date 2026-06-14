"""Unlock request dry-run workflow."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class UnlockRequest:
    request_id: str
    requested_at: str
    gate_type: str  # submit, cancel, reconciliation
    blockers: tuple[str, ...]
    decision: str  # DENY, BLOCKED, NOT_READY
    approved: bool
    def to_dict(self) -> dict:
        return {"request_id": self.request_id, "requested_at": self.requested_at, "gate_type": self.gate_type, "blockers": list(self.blockers), "decision": self.decision, "approved": self.approved}

SUBMIT_BLOCKERS = (
    "Real credential vault not implemented",
    "Real exchange adapter not implemented",
    "Real request signing not implemented",
    "Real network transport not implemented",
    "Field test not executed",
    "Human approval chain not completed",
    "Audit log external storage not verified",
    "Kill switch not field-tested",
    "Rollback not rehearsed",
)

CANCEL_BLOCKERS = (
    "Cancel idempotency not field-tested",
    "Unknown order handling not field-tested",
    "Terminal order handling not field-tested",
    "Emergency cancel not field-tested",
    "Cancel audit log not verified",
)

RECON_BLOCKERS = (
    "Real balance fetch not implemented",
    "Real position fetch not implemented",
    "Staleness threshold not field-tested",
    "Mismatch handling not field-tested",
    "Manual override policy not implemented",
)

def create_unlock_request(gate_type: str) -> UnlockRequest:
    blockers = {
        "submit": SUBMIT_BLOCKERS,
        "cancel": CANCEL_BLOCKERS,
        "reconciliation": RECON_BLOCKERS,
    }.get(gate_type, SUBMIT_BLOCKERS)
    return UnlockRequest(
        request_id=f"UNLOCK_{uuid.uuid4().hex[:12]}",
        requested_at=datetime.now(timezone.utc).isoformat(),
        gate_type=gate_type,
        blockers=blockers,
        decision="DENY",
        approved=False,
    )

def write_request(req: UnlockRequest, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(req.to_dict(), indent=2), encoding="utf-8")

def render_report() -> str:
    lines = ["# Unlock Request Dry-Run Workflow", "",
        "**unlock_mode=DRY_RUN_ONLY**",
        "**submit_gate_state=LOCKED**",
        "**cancel_gate_state=LOCKED**",
        "**reconciliation_gate_state=LOCKED**",
        "**approved=false**", "",
        "## Submit Gate Blockers", ""]
    for b in SUBMIT_BLOCKERS:
        lines.append(f"- {b}")
    lines.extend(["", "## Cancel Gate Blockers", ""])
    for b in CANCEL_BLOCKERS:
        lines.append(f"- {b}")
    lines.extend(["", "## Reconciliation Gate Blockers", ""])
    for b in RECON_BLOCKERS:
        lines.append(f"- {b}")
    lines.extend(["", "## Conclusion", "",
        "UNLOCK_REQUEST_DRY_RUN_WORKFLOW_READY",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
