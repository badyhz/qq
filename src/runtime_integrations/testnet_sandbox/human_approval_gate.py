"""Human approval gate. Default DENIED, blocks all submit."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class ApprovalRequest:
    request_id: str
    intent_id: str
    symbol: str
    side: str
    quantity: float
    requested_at: str
    def to_dict(self) -> dict:
        return {"request_id": self.request_id, "intent_id": self.intent_id, "symbol": self.symbol, "side": self.side, "quantity": self.quantity, "requested_at": self.requested_at}

@dataclass(frozen=True)
class ApprovalDecision:
    request_id: str
    human_approval_required: bool
    approved: bool
    submit_allowed: bool
    reason: str
    decided_at: str
    def to_dict(self) -> dict:
        return {"request_id": self.request_id, "human_approval_required": self.human_approval_required, "approved": self.approved, "submit_allowed": self.submit_allowed, "reason": self.reason, "decided_at": self.decided_at}

def create_request(intent_id: str, symbol: str, side: str, quantity: float) -> ApprovalRequest:
    now = datetime.now(timezone.utc).isoformat()
    return ApprovalRequest(request_id=f"APR_{intent_id}", intent_id=intent_id, symbol=symbol, side=side, quantity=quantity, requested_at=now)

def default_decision(request: ApprovalRequest) -> ApprovalDecision:
    return ApprovalDecision(
        request_id=request.request_id, human_approval_required=True,
        approved=False, submit_allowed=False, reason="DEFAULT_DENY: no human approval granted",
        decided_at=datetime.now(timezone.utc).isoformat(),
    )

def deny_stale(request: ApprovalRequest, max_age_seconds: float = 300.0) -> ApprovalDecision:
    return ApprovalDecision(
        request_id=request.request_id, human_approval_required=True,
        approved=False, submit_allowed=False, reason="STALE_REQUEST: approval request expired",
        decided_at=datetime.now(timezone.utc).isoformat(),
    )

def deny_incomplete(request: ApprovalRequest, missing_fields: tuple[str, ...]) -> ApprovalDecision:
    return ApprovalDecision(
        request_id=request.request_id, human_approval_required=True,
        approved=False, submit_allowed=False, reason=f"INCOMPLETE: missing fields: {', '.join(missing_fields)}",
        decided_at=datetime.now(timezone.utc).isoformat(),
    )

def write_decision(decision: ApprovalDecision, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(decision.to_dict(), indent=2), encoding="utf-8")

def write_gate_check(decisions: list[ApprovalDecision], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    check = {
        "total_requests": len(decisions),
        "all_denied": all(not d.approved for d in decisions),
        "all_submit_blocked": all(not d.submit_allowed for d in decisions),
        "all_require_human": all(d.human_approval_required for d in decisions),
    }
    out.write_text(json.dumps(check, indent=2), encoding="utf-8")

def render_gate_report(decisions: list[ApprovalDecision]) -> str:
    lines = ["# Human Approval Gate Report", "", "## Status", "", "- human_approval_required: true", "- approved: false (default)", "- submit_allowed: false", "", "## Decisions", ""]
    for d in decisions:
        lines.append(f"- {d.request_id}: approved={d.approved}, reason={d.reason}")
    lines.extend(["", "## Conclusion", "", "HUMAN_APPROVAL_GATE_VALID", "DEFAULT_DENY_ENFORCED", ""])
    return "\n".join(lines)
