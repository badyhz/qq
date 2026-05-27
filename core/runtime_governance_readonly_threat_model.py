"""T847 — Runtime governance read-only threat model.

Pure, deterministic. No I/O, no timestamps, no random.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyThreat:
    threat_id: str
    title: str
    severity: str  # "low", "medium", "high", "critical"
    vector: str
    mitigation: str
    status: str  # "open", "mitigated", "accepted"


_THREAT_DEFS: List[Dict[str, str]] = [
    {
        "threat_id": "readonly_bypass",
        "title": "Read-only bypass via permission escalation",
        "severity": "critical",
        "vector": "permission envelope manipulation",
        "mitigation": "invariant checker + permission envelope validation",
        "status": "open",
    },
    {
        "threat_id": "permission_creep",
        "title": "Permission creep beyond read-only",
        "severity": "high",
        "vector": "gradual permission expansion",
        "mitigation": "strict boundary enforcement + rollback plan",
        "status": "open",
    },
    {
        "threat_id": "secret_leak",
        "title": "Secret or credential leak in read-only layer",
        "severity": "critical",
        "vector": "observability data exposure",
        "mitigation": "redaction rules + encrypted storage for sensitive signals",
        "status": "open",
    },
    {
        "threat_id": "planner_override",
        "title": "Planner override of read-only constraints",
        "severity": "critical",
        "vector": "planner autonomous mode",
        "mitigation": "planner integration frozen + manual approval gate",
        "status": "open",
    },
    {
        "threat_id": "network_exfiltration",
        "title": "Network exfiltration via read-only hook",
        "severity": "high",
        "vector": "covert network channel",
        "mitigation": "network invariant checker + no network declaration",
        "status": "open",
    },
]


def build_readonly_threat_model() -> List[RuntimeGovernanceReadOnlyThreat]:
    """Build the canonical read-only threat model."""
    return [
        RuntimeGovernanceReadOnlyThreat(**d) for d in _THREAT_DEFS
    ]


def readonly_threat_model_to_dict(
    threats: List[RuntimeGovernanceReadOnlyThreat],
) -> List[Dict[str, str]]:
    """Convert threats to list of dicts."""
    return [
        {
            "threat_id": t.threat_id,
            "title": t.title,
            "severity": t.severity,
            "vector": t.vector,
            "mitigation": t.mitigation,
            "status": t.status,
        }
        for t in threats
    ]


def readonly_threat_model_to_markdown(
    threats: List[RuntimeGovernanceReadOnlyThreat],
) -> str:
    """Render threats as a markdown table."""
    lines: List[str] = [
        "# Runtime Governance Read-Only Threat Model",
        "",
        "| threat_id | title | severity | vector | mitigation | status |",
        "|---|---|---|---|---|---|",
    ]
    for t in threats:
        lines.append(
            f"| {t.threat_id} | {t.title} | {t.severity} "
            f"| {t.vector} | {t.mitigation} | {t.status} |"
        )
    return "\n".join(lines)


def summarize_readonly_threat_model(
    threats: List[RuntimeGovernanceReadOnlyThreat],
) -> Dict[str, object]:
    """Return summary counts for the threat model."""
    severity_counts: Dict[str, int] = {}
    status_counts: Dict[str, int] = {}
    for t in threats:
        severity_counts[t.severity] = severity_counts.get(t.severity, 0) + 1
        status_counts[t.status] = status_counts.get(t.status, 0) + 1
    return {
        "total": len(threats),
        "by_severity": severity_counts,
        "by_status": status_counts,
    }
