"""PRD 500 backlog risk map — deterministic risk summary.

T909. Pure deterministic, no I/O, no timestamps, no random.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_backlog_schema import PrdBacklog


# --- Dataclass ---


@dataclass(frozen=True)
class Prd500RiskMap:
    total_items: int
    low_count: int
    medium_count: int
    high_count: int
    frozen_count: int
    human_review_required_count: int
    recommended_action: str
    notes: List[str]


# --- Builder ---


def build_prd_500_risk_map(backlog: PrdBacklog) -> Prd500RiskMap:
    """Build risk map from backlog. Pure, deterministic."""
    low_count = 0
    medium_count = 0
    high_count = 0
    frozen_count = 0
    notes: List[str] = []

    for item in backlog.items:
        level = item.risk_level
        if level == "LOW":
            low_count += 1
        elif level == "MEDIUM":
            medium_count += 1
        elif level == "HIGH":
            high_count += 1
        elif level == "FROZEN":
            frozen_count += 1

    total_items = low_count + medium_count + high_count + frozen_count
    human_review_required_count = frozen_count + high_count

    if frozen_count > 0:
        recommended_action = "HUMAN_REVIEW_REQUIRED before any execution"
    elif high_count > 0:
        recommended_action = "STAGED_EXECUTION with human review for HIGH"
    else:
        recommended_action = "PROCEED with standard safety"

    if total_items != len(backlog.items):
        notes.append(
            f"count mismatch: computed {total_items} != len(items) {len(backlog.items)}"
        )

    return Prd500RiskMap(
        total_items=total_items,
        low_count=low_count,
        medium_count=medium_count,
        high_count=high_count,
        frozen_count=frozen_count,
        human_review_required_count=human_review_required_count,
        recommended_action=recommended_action,
        notes=notes,
    )


# --- Serializers ---


def risk_map_to_dict(risk_map: Prd500RiskMap) -> Dict[str, Any]:
    """Convert risk map to dict. Pure."""
    return {
        "total_items": risk_map.total_items,
        "low_count": risk_map.low_count,
        "medium_count": risk_map.medium_count,
        "high_count": risk_map.high_count,
        "frozen_count": risk_map.frozen_count,
        "human_review_required_count": risk_map.human_review_required_count,
        "recommended_action": risk_map.recommended_action,
        "notes": list(risk_map.notes),
    }


def risk_map_to_markdown(risk_map: Prd500RiskMap) -> str:
    """Convert risk map to markdown. Pure."""
    lines: List[str] = []
    lines.append("# PRD 500 Backlog Risk Map")
    lines.append("")
    lines.append(f"- **Total items:** {risk_map.total_items}")
    lines.append(f"- **LOW:** {risk_map.low_count}")
    lines.append(f"- **MEDIUM:** {risk_map.medium_count}")
    lines.append(f"- **HIGH:** {risk_map.high_count}")
    lines.append(f"- **FROZEN:** {risk_map.frozen_count}")
    lines.append(f"- **Human review required:** {risk_map.human_review_required_count}")
    lines.append(f"- **Recommended action:** {risk_map.recommended_action}")
    if risk_map.notes:
        lines.append("")
        lines.append("**Notes:**")
        for note in risk_map.notes:
            lines.append(f"- {note}")
    return "\n".join(lines)
