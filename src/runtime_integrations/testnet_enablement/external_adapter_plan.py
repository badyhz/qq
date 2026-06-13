"""External sandbox adapter implementation plan."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class PlanSection:
    section_id: str
    title: str
    content: str
    status: str = "DOCUMENTED"
    def to_dict(self) -> dict:
        return {"section_id": self.section_id, "title": self.title, "content": self.content, "status": self.status}

SECTIONS = (
    PlanSection("boundaries", "Adapter Boundaries", "Define clear boundary between simulation and real exchange. All methods must be simulation-only in this phase."),
    PlanSection("allowed_methods", "Allowed Future Methods", "load_connection_profile, validate_permissions, build_signed_request, submit_order, cancel_order, fetch_balance, fetch_positions, fetch_order_status"),
    PlanSection("forbidden_methods", "Forbidden Current Methods", "No real network calls, no real API keys, no real signatures, no real order submission"),
    PlanSection("network_transport", "Network Transport Requirements", "HTTPS only, TLS 1.2+, certificate pinning, request timeout, retry with backoff"),
    PlanSection("request_signing", "Request Signing Requirements", "HMAC-SHA256, timestamp validation, recvWindow parameter, canonical string construction"),
    PlanSection("credential_vault", "Credential Vault Requirements", "Encrypted at rest, access control, audit logging, key rotation, no environment variables"),
    PlanSection("rate_limits", "Rate Limit Requirements", "Per-endpoint limits, order rate limits, cancel rate limits, exponential backoff, cool-down"),
    PlanSection("cancel_safety", "Cancel Safety Requirements", "Idempotent cancel, terminal order handling, unknown order handling, audit trail"),
    PlanSection("reconciliation", "Reconciliation Requirements", "Real balance fetch, real position fetch, staleness detection, mismatch handling, manual override"),
    PlanSection("audit_logging", "Audit Logging Requirements", "Tamper-evident chain, external storage, retention policy, export capability"),
    PlanSection("human_approval", "Human Approval Requirements", "Multi-party approval, expiration, risk summary, cancel plan, rollback plan"),
    PlanSection("rollback", "Rollback Requirements", "Point-in-time restore, artifact preservation, audit log continuity"),
)

def get_sections() -> tuple[PlanSection, ...]:
    return SECTIONS

def get_plan_sections() -> tuple[PlanSection, ...]:
    return get_sections()

def write_plan(sections: tuple[PlanSection, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([s.to_dict() for s in sections], indent=2), encoding="utf-8")

def render_plan_report(sections: tuple[PlanSection, ...]) -> str:
    lines = ["# External Sandbox Adapter Implementation Plan", "", "**Phase: DESIGN_ONLY — No implementation in this phase**", "**Submit: NOT_ALLOWED**", ""]
    for s in sections:
        lines.extend([f"## {s.title}", "", s.content, ""])
    lines.extend(["## Conclusion", "", "EXTERNAL_SANDBOX_ADAPTER_PLAN_VALID", "NO_SUBMIT_ALLOWED", ""])
    return "\n".join(lines)
