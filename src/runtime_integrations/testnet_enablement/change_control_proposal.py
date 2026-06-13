"""Testnet submit change-control proposal."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class ChangeControlProposal:
    proposal_id: str
    created_at: str
    scope: str
    non_goals: tuple[str, ...]
    risk_assessment: str
    security_requirements: tuple[str, ...]
    credential_requirements: tuple[str, ...]
    human_approvals_required: tuple[str, ...]
    rollback_plan: str
    kill_switch_procedure: str
    audit_requirements: tuple[str, ...]
    dry_run_acceptance: tuple[str, ...]
    field_test_acceptance: tuple[str, ...]
    go_no_go_checklist: tuple[str, ...]
    def to_dict(self) -> dict:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        for k in ("non_goals", "security_requirements", "credential_requirements", "human_approvals_required", "audit_requirements", "dry_run_acceptance", "field_test_acceptance", "go_no_go_checklist"):
            d[k] = list(d[k])
        return d

def create_proposal() -> ChangeControlProposal:
    return ChangeControlProposal(
        proposal_id=f"CCP_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        scope="External sandbox adapter dry-run with real testnet endpoints",
        non_goals=("no real submit", "no real credentials in this phase", "no live trading", "no auto submit"),
        risk_assessment="HIGH — involves real testnet endpoints, requires full human approval chain",
        security_requirements=("encrypted credential vault", "IP allowlist", "TLS 1.2+", "certificate pinning", "audit logging"),
        credential_requirements=("testnet-only keys", "no withdraw permission", "read-only + trade only", "key rotation plan"),
        human_approvals_required=("operator_ack", "security_review", "risk_approval", "legal_review"),
        rollback_plan="Revert to last known good commit, disable testnet adapter, re-enable kill switch",
        kill_switch_procedure="ENABLED_BLOCKING by default, manual unlock requires 2-person approval",
        audit_requirements=("tamper-evident log", "external storage", "90-day retention", "export capability"),
        dry_run_acceptance=("all harness steps pass", "no real network calls", "all safety flags present"),
        field_test_acceptance=("testnet endpoint reachable", "credentials validated", "order lifecycle completes", "cancel works", "reconciliation matches"),
        go_no_go_checklist=("all blockers resolved", "human approval obtained", "kill switch tested", "rollback tested", "audit log verified"),
    )

def write_proposal(proposal: ChangeControlProposal, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proposal.to_dict(), indent=2), encoding="utf-8")

def render_report(proposal: ChangeControlProposal) -> str:
    lines = ["# Testnet Submit Change-Control Proposal", "", "## Scope", "", proposal.scope, "", "## Non-Goals", ""]
    for ng in proposal.non_goals:
        lines.append(f"- {ng}")
    lines.extend(["", "## Risk Assessment", "", proposal.risk_assessment, "", "## Conclusion", "", "CHANGE_CONTROL_PROPOSAL_VALID", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
