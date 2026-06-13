"""Approval decision types and validators."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ApprovalValidation:
    request_id: str
    checks: tuple[str, ...]
    valid: bool
    def to_dict(self) -> dict:
        return {"request_id": self.request_id, "checks": list(self.checks), "valid": self.valid}

def validate_approval_packet(packet: dict) -> ApprovalValidation:
    checks = []
    ok = True
    required = ("request_id", "human_approval_required", "approved", "submit_allowed", "reason")
    for f in required:
        if f in packet:
            checks.append(f"required_present: {f}")
        else:
            checks.append(f"REQUIRED_MISSING: {f}")
            ok = False
    if packet.get("approved") is True:
        checks.append("APPROVED_NOT_ALLOWED_IN_STUB")
        ok = False
    if packet.get("submit_allowed") is True:
        checks.append("SUBMIT_ALLOWED_NOT_ALLOWED_IN_STUB")
        ok = False
    if packet.get("human_approval_required") is not True:
        checks.append("HUMAN_APPROVAL_REQUIRED_MUST_BE_TRUE")
        ok = False
    return ApprovalValidation(packet.get("request_id", "unknown"), tuple(checks), ok)

def write_validation(val: ApprovalValidation, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(val.to_dict(), indent=2), encoding="utf-8")
