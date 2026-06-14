"""External testnet adapter design specification."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class AdapterSpecSection:
    section_id: str
    title: str
    content: str
    def to_dict(self) -> dict:
        return {"section_id": self.section_id, "title": self.title, "content": self.content}

SECTIONS = (
    AdapterSpecSection("purpose", "Adapter Purpose", "Provide a safe, auditable interface to Binance testnet for order lifecycle management. Design-only phase — no implementation."),
    AdapterSpecSection("non_goals", "Non-Goals", "No real submit, no real credentials, no live trading, no auto-submit, no real network calls in this phase."),
    AdapterSpecSection("exchange_profile", "Supported Future Exchange Profile", "Binance testnet (testnet.binance.vision) only; no production endpoints. Spot and USDⓈ-M futures. REST API v3/v1. HMAC-SHA256 signing."),
    AdapterSpecSection("method_boundaries", "Future Method Boundaries", "load_connection_profile, validate_permissions, build_signed_request, submit_order, cancel_order, fetch_balance, fetch_positions, fetch_order_status, reconcile."),
    AdapterSpecSection("forbidden_methods", "Forbidden Current Methods", "No real network calls, no real API keys, no real signatures, no real order submission, no ccxt client instantiation. Submit remains locked and testnet submit is not allowed until governance unlock."),
    AdapterSpecSection("credential_dep", "Credential Dependency", "Requires encrypted credential vault with access control, audit logging, key rotation, and redaction. Not implemented in this phase."),
    AdapterSpecSection("signing_dep", "Request Signing Dependency", "Requires HMAC-SHA256 canonical request construction with timestamp, nonce, and payload hash. Not implemented in this phase."),
    AdapterSpecSection("network_dep", "Network Transport Dependency", "Requires HTTPS-only transport with TLS 1.2+, certificate pinning, timeout, retry, and rate limiting. Not implemented in this phase."),
    AdapterSpecSection("rate_limit_dep", "Rate Limit Dependency", "Requires per-endpoint rate limits with exponential backoff and cool-down. Not implemented in this phase."),
    AdapterSpecSection("cancel_dep", "Cancel Dependency", "Requires idempotent cancel, terminal order handling, unknown order handling, and cancel audit trail. Not implemented in this phase."),
    AdapterSpecSection("recon_dep", "Reconciliation Dependency", "Requires real balance/position fetch, staleness detection, mismatch handling, and manual override. Not implemented in this phase."),
    AdapterSpecSection("audit_dep", "Audit Dependency", "Requires tamper-evident hash chain, external storage, 90-day retention, and export capability. Not implemented in this phase."),
    AdapterSpecSection("approval_dep", "Human Approval Dependency", "Requires multi-party approval with expiration, risk summary, cancel plan, and rollback plan. Not implemented in this phase."),
    AdapterSpecSection("kill_switch_dep", "Kill Switch Dependency", "Requires kill switch armed by default, blocking all submits, with manual 2-person unlock. Not implemented in this phase."),
    AdapterSpecSection("rollback_dep", "Rollback Dependency", "Requires point-in-time restore, artifact preservation, and audit log continuity. Not implemented in this phase."),
)

def get_sections() -> tuple[AdapterSpecSection, ...]:
    return SECTIONS

def write_spec(sections: tuple[AdapterSpecSection, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([s.to_dict() for s in sections], indent=2), encoding="utf-8")

def render_report(sections: tuple[AdapterSpecSection, ...]) -> str:
    lines = ["# External Testnet Adapter Design Specification", "", "**Phase: DESIGN_ONLY — No implementation in this phase**", "**Submit: TESTNET_SUBMIT_NOT_ALLOWED**", "**Adapter Mode: ARCHITECTURE_ONLY**", ""]
    for s in sections:
        lines.extend([f"## {s.title}", "", s.content, ""])
    lines.extend(["## Conclusion", "", "EXTERNAL_TESTNET_ADAPTER_SPEC_VALID", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
