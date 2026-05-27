"""T846: Runtime governance read-only observability design.

Static, deterministic design for future read-only observation layer.
No I/O, no timestamps, no random, no logging implementation.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyObservationPoint:
    point_id: str
    signal: str
    sensitivity: str  # "low", "medium", "high", "critical"
    allowed_storage: str
    redaction: str
    notes: List[str]


_OBSERVATION_POINTS: List[RuntimeGovernanceReadOnlyObservationPoint] = [
    RuntimeGovernanceReadOnlyObservationPoint(
        point_id="permission_check",
        signal="permission envelope evaluation",
        sensitivity="low",
        allowed_storage="local log",
        redaction="none",
        notes=["evaluates permission envelope against policy"],
    ),
    RuntimeGovernanceReadOnlyObservationPoint(
        point_id="invariant_result",
        signal="invariant checker result",
        sensitivity="low",
        allowed_storage="local log",
        redaction="none",
        notes=["result of invariant validation checks"],
    ),
    RuntimeGovernanceReadOnlyObservationPoint(
        point_id="scenario_verdict",
        signal="scenario evaluation verdict",
        sensitivity="low",
        allowed_storage="local log",
        redaction="none",
        notes=["verdict from scenario evaluation engine"],
    ),
    RuntimeGovernanceReadOnlyObservationPoint(
        point_id="blocker_summary",
        signal="blocker summary",
        sensitivity="medium",
        allowed_storage="local log",
        redaction="none",
        notes=["summary of active blockers"],
    ),
    RuntimeGovernanceReadOnlyObservationPoint(
        point_id="readiness_score",
        signal="readiness score",
        sensitivity="medium",
        allowed_storage="local log",
        redaction="none",
        notes=["computed readiness score for phase transition"],
    ),
    RuntimeGovernanceReadOnlyObservationPoint(
        point_id="phase_decision",
        signal="phase control decision",
        sensitivity="high",
        allowed_storage="encrypted",
        redaction="none",
        notes=["decision made by phase control logic"],
    ),
    RuntimeGovernanceReadOnlyObservationPoint(
        point_id="approval_status",
        signal="approval form status",
        sensitivity="critical",
        allowed_storage="encrypted",
        redaction="full",
        notes=["approval form state; requires full redaction"],
    ),
]


def build_readonly_observability_design() -> List[RuntimeGovernanceReadOnlyObservationPoint]:
    """Return the static list of observation points. Pure, deterministic."""
    return list(_OBSERVATION_POINTS)


def readonly_observability_design_to_dict(
    points: List[RuntimeGovernanceReadOnlyObservationPoint],
) -> List[Dict]:
    """Convert observation points to list of dicts. Pure, deterministic."""
    return [asdict(p) for p in points]


def readonly_observability_design_to_markdown(
    points: List[RuntimeGovernanceReadOnlyObservationPoint],
) -> str:
    """Render observation points as markdown table. Pure, deterministic."""
    lines = [
        "| point_id | signal | sensitivity | allowed_storage | redaction |",
        "|---|---|---|---|---|",
    ]
    for p in points:
        lines.append(
            f"| {p.point_id} | {p.signal} | {p.sensitivity} "
            f"| {p.allowed_storage} | {p.redaction} |"
        )
    return "\n".join(lines) + "\n"
