"""Threat model and security review checklist."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ThreatItem:
    threat_id: str
    category: str
    description: str
    mitigation: str
    status: str  # DESIGNED, MITIGATED, ACCEPTED, OPEN
    def to_dict(self) -> dict:
        return {"threat_id": self.threat_id, "category": self.category, "description": self.description, "mitigation": self.mitigation, "status": self.status}

THREATS = (
    ThreatItem("cred_leak", "credential_leakage", "API secret leaked through logs, errors, or debug output", "Redaction policy, audit logging, secret scanning", "DESIGNED"),
    ThreatItem("perm_overreach", "permission_overreach", "API key granted more permissions than needed", "Least privilege, permission review, withdraw forbidden", "DESIGNED"),
    ThreatItem("withdraw_exposure", "withdraw_permission_exposure", "Withdraw permission accidentally enabled", "Explicit deny, automated check, revocation policy", "DESIGNED"),
    ThreatItem("replay_attack", "replay_attack", "Signed request replayed by attacker", "Timestamp + nonce, server-side dedup, short TTL", "DESIGNED"),
    ThreatItem("duplicate_submit", "duplicate_submit", "Order submitted multiple times", "Idempotency key, server-side dedup, client-side dedup", "DESIGNED"),
    ThreatItem("stale_signal", "stale_signal_submit", "Order submitted based on stale signal", "Signal staleness check, timestamp validation", "DESIGNED"),
    ThreatItem("network_timeout", "network_timeout", "Request times out, unknown state", "Timeout policy, retry with backoff, idempotency", "DESIGNED"),
    ThreatItem("partial_response", "partial_response", "Server returns partial response", "Response validation, reject partial, retry", "DESIGNED"),
    ThreatItem("cancel_failure", "cancel_failure", "Cancel request fails, order remains open", "Cancel retry, emergency cancel, operator alert", "DESIGNED"),
    ThreatItem("recon_mismatch", "reconciliation_mismatch", "Local state differs from exchange state", "Reconciliation cycle, mismatch alert, order hold", "DESIGNED"),
    ThreatItem("audit_tamper", "audit_tampering", "Audit log tampered or deleted", "Tamper-evident chain, external storage, backup", "DESIGNED"),
    ThreatItem("operator_error", "operator_error", "Operator makes mistake (wrong symbol, wrong size)", "Approval workflow, notional cap, symbol allowlist", "DESIGNED"),
    ThreatItem("approval_spoof", "approval_spoofing", "Fake approval submitted", "Authenticated approval, MFA, audit trail", "DESIGNED"),
    ThreatItem("kill_switch_fail", "kill_switch_failure", "Kill switch fails to block submit", "Default blocking, regular testing, redundant check", "DESIGNED"),
    ThreatItem("rollback_fail", "rollback_failure", "Rollback fails or corrupts state", "Rollback rehearsal, artifact preservation, backup", "DESIGNED"),
)

def get_threats() -> tuple[ThreatItem, ...]:
    return THREATS

def write_threats(threats: tuple[ThreatItem, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([t.to_dict() for t in threats], indent=2), encoding="utf-8")

def render_report(threats: tuple[ThreatItem, ...]) -> str:
    lines = ["# Threat Model and Security Review Checklist", "",
        "**Status: THREAT_MODEL_SECURITY_REVIEW_READY**",
        "**Submit: TESTNET_SUBMIT_NOT_ALLOWED**", ""]
    lines.append("| Threat | Category | Status |")
    lines.append("|--------|----------|--------|")
    for t in threats:
        lines.append(f"| {t.description} | {t.category} | {t.status} |")
    lines.extend(["", "## Conclusion", "", "THREAT_MODEL_SECURITY_REVIEW_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
