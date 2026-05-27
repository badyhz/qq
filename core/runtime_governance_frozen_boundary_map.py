"""Runtime governance frozen boundary map — document frozen boundaries as data."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceFrozenBoundary:
    boundary_id: str
    path_pattern: str
    reason: str
    allowed_action: str
    status: str  # "frozen"


def build_runtime_governance_frozen_boundary_map() -> List[RuntimeGovernanceFrozenBoundary]:
    """Return the canonical list of frozen boundaries."""
    return [
        RuntimeGovernanceFrozenBoundary(
            boundary_id="live_trading",
            path_pattern="scripts/*live*",
            reason="no live trading",
            allowed_action="read only",
            status="frozen",
        ),
        RuntimeGovernanceFrozenBoundary(
            boundary_id="submit_scripts",
            path_pattern="scripts/submit*",
            reason="no submit",
            allowed_action="read only",
            status="frozen",
        ),
        RuntimeGovernanceFrozenBoundary(
            boundary_id="secrets",
            path_pattern="*.env, *credentials*, *secret*",
            reason="no secret access",
            allowed_action="none",
            status="frozen",
        ),
        RuntimeGovernanceFrozenBoundary(
            boundary_id="planner",
            path_pattern="core/planner*",
            reason="planner integration frozen",
            allowed_action="read only",
            status="frozen",
        ),
        RuntimeGovernanceFrozenBoundary(
            boundary_id="runtime_execution",
            path_pattern="core/live_runner.py",
            reason="runtime execution frozen",
            allowed_action="read only",
            status="frozen",
        ),
        RuntimeGovernanceFrozenBoundary(
            boundary_id="exchange_client",
            path_pattern="core/exchange*",
            reason="exchange client mutation frozen",
            allowed_action="read only",
            status="frozen",
        ),
    ]


def frozen_boundary_map_to_dict(boundaries: List[RuntimeGovernanceFrozenBoundary]) -> List[Dict]:
    """Convert frozen boundary list to list of dicts."""
    return [asdict(b) for b in boundaries]


def frozen_boundary_map_to_markdown(boundaries: List[RuntimeGovernanceFrozenBoundary]) -> str:
    """Render frozen boundary list as a markdown table."""
    lines = [
        "| boundary_id | path_pattern | reason | allowed_action | status |",
        "|---|---|---|---|---|",
    ]
    for b in boundaries:
        lines.append(
            f"| {b.boundary_id} | {b.path_pattern} | {b.reason} | {b.allowed_action} | {b.status} |"
        )
    return "\n".join(lines)
