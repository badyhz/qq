"""Runtime governance integration risk register — track integration risks.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceIntegrationRisk:
    """Single integration risk entry."""

    risk_id: str
    description: str
    severity: str  # "LOW" / "MEDIUM" / "HIGH" / "CRITICAL"
    status: str  # "OPEN" / "MITIGATED" / "CLOSED"


@dataclass(frozen=True)
class RuntimeGovernanceIntegrationRiskRegister:
    """Immutable integration risk register for runtime governance."""

    title: str
    risks: List[RuntimeGovernanceIntegrationRisk]
    verdict: str  # "PASS" / "WARN" / "FAIL"
    notes: List[str] = field(default_factory=list)


_DEFAULT_RISKS: List[Dict[str, str]] = [
    {"risk_id": "R1", "description": "network_partition", "severity": "LOW", "status": "MITIGATED"},
    {"risk_id": "R2", "description": "rate_limit_exceeded", "severity": "LOW", "status": "MITIGATED"},
    {"risk_id": "R3", "description": "config_drift", "severity": "LOW", "status": "MITIGATED"},
]


def build_runtime_governance_integration_risk_register(
    *,
    title: str = "Runtime Governance Integration Risk Register",
    risks: List[RuntimeGovernanceIntegrationRisk] | None = None,
    verdict: str | None = None,
    notes: List[str] | None = None,
) -> RuntimeGovernanceIntegrationRiskRegister:
    """Build integration risk register. Pure. No I/O.

    Defaults produce a register with all risks mitigated (PASS).
    """
    if risks is None:
        risks = [
            RuntimeGovernanceIntegrationRisk(**spec)
            for spec in _DEFAULT_RISKS
        ]

    eff_verdict = verdict if verdict is not None else _compute_verdict(risks)

    return RuntimeGovernanceIntegrationRiskRegister(
        title=title,
        risks=risks,
        verdict=eff_verdict,
        notes=list(notes) if notes else [],
    )


def summarize_risk_register(register: RuntimeGovernanceIntegrationRiskRegister) -> Dict[str, Any]:
    """Summarize risk register counts. Deterministic."""
    by_severity: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    for r in register.risks:
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1

    return {
        "total": len(register.risks),
        "by_status": dict(sorted(by_status.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "verdict": register.verdict,
    }


def risk_register_to_dict(register: RuntimeGovernanceIntegrationRiskRegister) -> Dict[str, Any]:
    """Serialize to dict. Pure."""
    return {
        "title": register.title,
        "risks": [
            {
                "risk_id": r.risk_id,
                "description": r.description,
                "severity": r.severity,
                "status": r.status,
            }
            for r in register.risks
        ],
        "verdict": register.verdict,
        "notes": list(register.notes),
    }


def risk_register_to_markdown(register: RuntimeGovernanceIntegrationRiskRegister) -> str:
    """Render as deterministic markdown. No timestamps."""
    lines: List[str] = [f"# {register.title}", ""]
    lines.append(f"**Verdict:** {register.verdict}")
    lines.append("")
    lines.append("| Risk ID | Description | Severity | Status |")
    lines.append("|---------|-------------|----------|--------|")
    for r in register.risks:
        lines.append(f"| {r.risk_id} | {r.description} | {r.severity} | {r.status} |")
    lines.append("")
    if register.notes:
        lines.append("## Notes")
        lines.append("")
        for note in register.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


# ── internal ───────────────────────────────────────────────────────


def _compute_verdict(risks: List[RuntimeGovernanceIntegrationRisk]) -> str:
    has_open_critical = any(
        r.severity == "CRITICAL" and r.status == "OPEN" for r in risks
    )
    has_open_high = any(
        r.severity == "HIGH" and r.status == "OPEN" for r in risks
    )
    has_open = any(r.status == "OPEN" for r in risks)

    if has_open_critical:
        return "FAIL"
    if has_open_high:
        return "WARN"
    if has_open:
        return "WARN"
    return "PASS"
