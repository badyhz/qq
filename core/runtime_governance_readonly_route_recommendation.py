"""Runtime governance read-only route recommendation — route/model recommendation for future work."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceRouteRecommendation:
    work_type: str
    recommended_route: str
    allowed: bool
    risk_level: str  # "low", "medium", "high", "critical"
    notes: List[str]


def build_readonly_route_recommendations() -> List[RuntimeGovernanceRouteRecommendation]:
    """Return the canonical list of route recommendations for governance."""
    return [
        RuntimeGovernanceRouteRecommendation(
            work_type="pure docs/tests",
            recommended_route="mimo2.5",
            allowed=True,
            risk_level="low",
            notes=["No dangerous operations"],
        ),
        RuntimeGovernanceRouteRecommendation(
            work_type="multi-wave dependency queue",
            recommended_route="mimo2.5pro",
            allowed=True,
            risk_level="medium",
            notes=["Requires API freeze rule"],
        ),
        RuntimeGovernanceRouteRecommendation(
            work_type="live execution",
            recommended_route="human only",
            allowed=False,
            risk_level="critical",
            notes=["Frozen - no autonomous execution"],
        ),
        RuntimeGovernanceRouteRecommendation(
            work_type="secrets management",
            recommended_route="human only",
            allowed=False,
            risk_level="critical",
            notes=["Frozen - no secret access"],
        ),
        RuntimeGovernanceRouteRecommendation(
            work_type="read-only hook implementation",
            recommended_route="mimo2.5pro with manual review",
            allowed=False,
            risk_level="high",
            notes=["Requires manual approval first"],
        ),
    ]


def route_recommendations_to_dict(
    recommendations: List[RuntimeGovernanceRouteRecommendation],
) -> List[Dict]:
    """Convert route recommendation list to list of dicts."""
    return [asdict(r) for r in recommendations]


def route_recommendations_to_markdown(
    recommendations: List[RuntimeGovernanceRouteRecommendation],
) -> str:
    """Render route recommendation list as a markdown table."""
    lines = [
        "| work_type | recommended_route | allowed | risk_level | notes |",
        "|---|---|---|---|---|",
    ]
    for r in recommendations:
        notes_str = "; ".join(r.notes)
        allowed_str = "yes" if r.allowed else "no"
        lines.append(
            f"| {r.work_type} | {r.recommended_route} | {allowed_str} | {r.risk_level} | {notes_str} |"
        )
    return "\n".join(lines)
