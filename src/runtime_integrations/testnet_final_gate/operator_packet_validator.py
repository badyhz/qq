"""Operator packet validator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

@dataclass(frozen=True)
class PacketCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def validate_packet_completeness(packet: dict) -> list[PacketCheck]:
    checks = []
    required = ("packet_id", "operator_id", "reviewer_id", "created_at", "expires_at",
                "submit_intent_summary", "credential_review_summary", "risk_control_summary",
                "kill_switch_summary", "cancel_plan_summary", "reconciliation_summary",
                "audit_log_summary", "rollback_plan", "emergency_procedure_reference", "no_submit_declaration")
    for f in required:
        checks.append(PacketCheck(f"has_{f}", f in packet and bool(packet[f]), f"{'present' if f in packet and packet[f] else 'MISSING'}"))
    # Stale check
    if "expires_at" in packet:
        try:
            exp = datetime.fromisoformat(packet["expires_at"])
            stale = exp < datetime.now(timezone.utc)
            checks.append(PacketCheck("not_stale", not stale, "stale" if stale else "valid"))
        except Exception:
            checks.append(PacketCheck("not_stale", False, "invalid_expires_at"))
    # Reviewer check
    checks.append(PacketCheck("has_reviewer", bool(packet.get("reviewer_id")), "reviewer present" if packet.get("reviewer_id") else "MISSING"))
    # Rollback check
    checks.append(PacketCheck("has_rollback", bool(packet.get("rollback_plan")), "rollback present" if packet.get("rollback_plan") else "MISSING"))
    # No-submit declaration
    checks.append(PacketCheck("has_no_submit_decl", bool(packet.get("no_submit_declaration")), "declaration present" if packet.get("no_submit_declaration") else "MISSING"))
    return checks

def write_checks(checks: list[PacketCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
