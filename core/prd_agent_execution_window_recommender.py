"""PRD agent execution window recommender — T879.

Pure, deterministic, no I/O, no timestamps, no random.
Recommends safe task execution window sizes based on risk and dependency density.
"""

from dataclasses import dataclass
from typing import Dict, List

from core.prd_backlog_schema import PrdBacklogItem

# --- Constants ---

VALID_RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "FROZEN")
VALID_DENSITY_LEVELS = ("low", "medium", "high")

# risk_level -> dependency_density -> (min, max, max_agents, route)
_WINDOW_TABLE = {
    "LOW": {
        "low":    (20, 50, 8, "mimo2.5pro or mimo2.5"),
        "medium": (15, 40, 7, "mimo2.5pro or mimo2.5"),
        "high":   (10, 30, 6, "mimo2.5pro"),
    },
    "MEDIUM": {
        "low":    (10, 30, 6, "mimo2.5pro"),
        "medium": (8,  25, 5, "mimo2.5pro"),
        "high":   (5,  20, 4, "mimo2.5pro"),
    },
    "HIGH": {
        "low":    (3, 10, 3, "mimo2.5pro with human review"),
        "medium": (2, 8,  2, "mimo2.5pro with human review"),
        "high":   (1, 5,  2, "mimo2.5pro with human review"),
    },
    "FROZEN": {
        "low":    (0, 0, 0, "HUMAN_ONLY"),
        "medium": (0, 0, 0, "HUMAN_ONLY"),
        "high":   (0, 0, 0, "HUMAN_ONLY"),
    },
}

# risk_level -> hard_stop_required
_HARD_STOP_MAP = {
    "LOW": False,
    "MEDIUM": False,
    "HIGH": True,
    "FROZEN": True,
}

# risk ordering for "highest wins"
_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "FROZEN": 3}


# --- Dataclass ---


@dataclass(frozen=True)
class PrdExecutionWindowRecommendation:
    risk_level: str
    dependency_density: str
    recommended_task_count_min: int
    recommended_task_count_max: int
    recommended_agent_count_max: int
    recommended_route: str
    hard_stop_required: bool
    notes: List[str]


# --- Core functions ---


def recommend_execution_window(
    risk_level: str,
    dependency_density: str,
) -> PrdExecutionWindowRecommendation:
    """Recommend execution window for given risk level and dependency density.

    Pure, deterministic, no I/O.
    """
    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(
            f"Invalid risk_level={risk_level!r}, must be one of {VALID_RISK_LEVELS}"
        )
    if dependency_density not in VALID_DENSITY_LEVELS:
        raise ValueError(
            f"Invalid dependency_density={dependency_density!r}, must be one of {VALID_DENSITY_LEVELS}"
        )

    row = _WINDOW_TABLE[risk_level][dependency_density]
    min_tasks, max_tasks, max_agents, route = row

    notes: List[str] = []
    if risk_level == "FROZEN":
        notes.append("FROZEN: no automated tasks allowed, human-only execution")
    elif risk_level == "HIGH":
        notes.append("HIGH risk: human review required before execution")
    if dependency_density == "high":
        notes.append("High dependency density: expect ordering constraints")

    return PrdExecutionWindowRecommendation(
        risk_level=risk_level,
        dependency_density=dependency_density,
        recommended_task_count_min=min_tasks,
        recommended_task_count_max=max_tasks,
        recommended_agent_count_max=max_agents,
        recommended_route=route,
        hard_stop_required=_HARD_STOP_MAP[risk_level],
        notes=notes,
    )


def recommend_window_for_tasks(
    items: List[PrdBacklogItem],
) -> PrdExecutionWindowRecommendation:
    """Recommend window for a list of backlog items.

    Uses highest risk level found and highest dependency density.
    Pure, deterministic, no I/O.
    """
    if not items:
        return recommend_execution_window("LOW", "low")

    # Find highest risk
    highest_risk = max(items, key=lambda i: _RISK_ORDER.get(i.risk_level, 0))
    risk = highest_risk.risk_level

    # Estimate dependency density: ratio of items with dependencies
    dep_count = sum(1 for i in items if i.dependencies)
    ratio = dep_count / len(items) if items else 0.0
    if ratio >= 0.5:
        density = "high"
    elif ratio >= 0.2:
        density = "medium"
    else:
        density = "low"

    return recommend_execution_window(risk, density)


# --- Serializers ---


def execution_window_to_dict(
    rec: PrdExecutionWindowRecommendation,
) -> Dict:
    """Convert recommendation to plain dict. Pure."""
    return {
        "risk_level": rec.risk_level,
        "dependency_density": rec.dependency_density,
        "recommended_task_count_min": rec.recommended_task_count_min,
        "recommended_task_count_max": rec.recommended_task_count_max,
        "recommended_agent_count_max": rec.recommended_agent_count_max,
        "recommended_route": rec.recommended_route,
        "hard_stop_required": rec.hard_stop_required,
        "notes": list(rec.notes),
    }


def execution_window_to_markdown(
    rec: PrdExecutionWindowRecommendation,
) -> str:
    """Convert recommendation to markdown table. Pure."""
    lines = [
        "## Execution Window Recommendation",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Risk Level | {rec.risk_level} |",
        f"| Dependency Density | {rec.dependency_density} |",
        f"| Task Count Range | {rec.recommended_task_count_min}-{rec.recommended_task_count_max} |",
        f"| Max Agents | {rec.recommended_agent_count_max} |",
        f"| Recommended Route | {rec.recommended_route} |",
        f"| Hard Stop Required | {'yes' if rec.hard_stop_required else 'no'} |",
    ]
    if rec.notes:
        lines.append("")
        lines.append("**Notes:**")
        for note in rec.notes:
            lines.append(f"- {note}")
    return "\n".join(lines) + "\n"
