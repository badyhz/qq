"""Runtime governance integration risk register — pure risk data.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceIntegrationRisk:
    """Single risk entry."""
    risk_id: str
    title: str
    severity: str  # "low", "medium", "high", "critical"
    likelihood: str  # "low", "medium", "high"
    mitigation: str
    status: str  # "open", "mitigated", "accepted"


_RISKS = [
    RuntimeGovernanceIntegrationRisk(
        risk_id="accidental_submit",
        title="Accidental submit to live exchange",
        severity="critical",
        likelihood="high",
        mitigation="No-submit guard, frozen boundaries, manual approval gate",
        status="open",
    ),
    RuntimeGovernanceIntegrationRisk(
        risk_id="network_permission_leak",
        title="Network permission leak outside governance",
        severity="high",
        likelihood="high",
        mitigation="Network blocked without explicit mode, invariant checker",
        status="open",
    ),
    RuntimeGovernanceIntegrationRisk(
        risk_id="stale_governance_verdict",
        title="Stale governance verdict used for decision",
        severity="medium",
        likelihood="medium",
        mitigation="Deterministic re-evaluation, no caching of verdicts",
        status="open",
    ),
    RuntimeGovernanceIntegrationRisk(
        risk_id="missing_manual_approval",
        title="Missing manual approval before phase advance",
        severity="high",
        likelihood="high",
        mitigation="Approval gate spec, transition checklist, phase control report",
        status="open",
    ),
    RuntimeGovernanceIntegrationRisk(
        risk_id="planner_bypass",
        title="Planner bypasses governance checks",
        severity="critical",
        likelihood="high",
        mitigation="Planner integration frozen, no autonomous planner mode",
        status="open",
    ),
    RuntimeGovernanceIntegrationRisk(
        risk_id="secret_exposure",
        title="Secret or credential exposure",
        severity="critical",
        likelihood="medium",
        mitigation="No secret access in governance layer, frozen boundary",
        status="open",
    ),
    RuntimeGovernanceIntegrationRisk(
        risk_id="untracked_file_io",
        title="Untracked file I/O in governance modules",
        severity="medium",
        likelihood="medium",
        mitigation="All modules declared pure, no-submit evidence packet",
        status="open",
    ),
    RuntimeGovernanceIntegrationRisk(
        risk_id="nondeterministic_evidence",
        title="Nondeterministic evidence invalidates audit",
        severity="low",
        likelihood="medium",
        mitigation="Deterministic builders, no timestamps, no random",
        status="open",
    ),
]


def build_runtime_governance_integration_risk_register() -> List[RuntimeGovernanceIntegrationRisk]:
    """Build risk register. Deterministic."""
    return list(_RISKS)


def risk_register_to_dict(register: List[RuntimeGovernanceIntegrationRisk]) -> List[Dict[str, Any]]:
    """Serialize to list of dicts."""
    return [
        {
            "risk_id": r.risk_id,
            "title": r.title,
            "severity": r.severity,
            "likelihood": r.likelihood,
            "mitigation": r.mitigation,
            "status": r.status,
        }
        for r in register
    ]


def risk_register_to_markdown(register: List[RuntimeGovernanceIntegrationRisk]) -> str:
    """Render as deterministic markdown."""
    lines = [
        "# Runtime Governance Integration Risk Register",
        "",
        "| Risk ID | Title | Severity | Likelihood | Status |",
        "|---------|-------|----------|------------|--------|",
    ]
    for r in register:
        lines.append(f"| {r.risk_id} | {r.title} | {r.severity} | {r.likelihood} | {r.status} |")
    lines.append("")
    if register:
        lines.append("## Mitigations")
        lines.append("")
        for r in register:
            lines.append(f"- **{r.risk_id}:** {r.mitigation}")
        lines.append("")
    return "\n".join(lines)


def summarize_risk_register(register: List[RuntimeGovernanceIntegrationRisk]) -> Dict[str, Any]:
    """Summarize risk register. Deterministic."""
    by_severity: Dict[str, int] = {}
    by_likelihood: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    for r in register:
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        by_likelihood[r.likelihood] = by_likelihood.get(r.likelihood, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
    return {
        "total": len(register),
        "by_severity": dict(sorted(by_severity.items())),
        "by_likelihood": dict(sorted(by_likelihood.items())),
        "by_status": dict(sorted(by_status.items())),
    }
