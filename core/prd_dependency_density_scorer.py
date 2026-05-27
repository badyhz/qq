"""PRD dependency density scorer — T892.

Pure, deterministic, no I/O, no timestamps, no random.
Scores dependency density for backlog items.
"""

from dataclasses import dataclass
from typing import Dict, List

from core.prd_backlog_schema import PrdBacklogItem

# --- Constants ---

DENSITY_THRESHOLDS = {
    "low": (0.0, 0.2),
    "medium": (0.2, 0.5),
    "high": (0.5, 1.01),
}


# --- Dataclass ---


@dataclass(frozen=True)
class PrdDependencyDensityScore:
    item_count: int
    total_dependency_count: int
    avg_dependencies_per_item: float
    density_ratio: float
    density_level: str
    items_with_deps_count: int
    isolated_item_count: int
    notes: List[str]


# --- Core functions ---


def score_dependency_density(items: List[PrdBacklogItem]) -> PrdDependencyDensityScore:
    """Score dependency density across a list of backlog items.

    Pure, deterministic, no I/O.
    """
    item_count = len(items)
    notes: List[str] = []

    if item_count == 0:
        notes.append("Empty item list, all metrics are zero")
        return PrdDependencyDensityScore(
            item_count=0,
            total_dependency_count=0,
            avg_dependencies_per_item=0.0,
            density_ratio=0.0,
            density_level="low",
            items_with_deps_count=0,
            isolated_item_count=0,
            notes=notes,
        )

    total_dependency_count = sum(len(i.dependencies) for i in items)
    items_with_deps_count = sum(1 for i in items if i.dependencies)
    isolated_item_count = item_count - items_with_deps_count
    avg_deps = total_dependency_count / item_count
    density_ratio = items_with_deps_count / item_count

    # Classify density level
    density_level = "low"
    for level, (lo, hi) in DENSITY_THRESHOLDS.items():
        if lo <= density_ratio < hi:
            density_level = level
            break

    if isolated_item_count == item_count:
        notes.append("All items are isolated — no dependencies found")
    elif isolated_item_count == 0:
        notes.append("Every item has at least one dependency")

    return PrdDependencyDensityScore(
        item_count=item_count,
        total_dependency_count=total_dependency_count,
        avg_dependencies_per_item=round(avg_deps, 4),
        density_ratio=round(density_ratio, 4),
        density_level=density_level,
        items_with_deps_count=items_with_deps_count,
        isolated_item_count=isolated_item_count,
        notes=notes,
    )


def score_density_for_milestone(
    items: List[PrdBacklogItem],
    milestone_id: str,
) -> PrdDependencyDensityScore:
    """Score dependency density for items filtered by milestone_id.

    Pure, deterministic, no I/O.
    """
    filtered = [i for i in items if i.milestone_id == milestone_id]
    return score_dependency_density(filtered)


# --- Serializers ---


def density_score_to_dict(score: PrdDependencyDensityScore) -> Dict:
    """Convert density score to plain dict. Pure."""
    return {
        "item_count": score.item_count,
        "total_dependency_count": score.total_dependency_count,
        "avg_dependencies_per_item": score.avg_dependencies_per_item,
        "density_ratio": score.density_ratio,
        "density_level": score.density_level,
        "items_with_deps_count": score.items_with_deps_count,
        "isolated_item_count": score.isolated_item_count,
        "notes": list(score.notes),
    }


def density_score_to_markdown(score: PrdDependencyDensityScore) -> str:
    """Convert density score to markdown table. Pure."""
    lines = [
        "## Dependency Density Score",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Item Count | {score.item_count} |",
        f"| Total Dependencies | {score.total_dependency_count} |",
        f"| Avg Dependencies/Item | {score.avg_dependencies_per_item} |",
        f"| Density Ratio | {score.density_ratio} |",
        f"| Density Level | {score.density_level} |",
        f"| Items With Deps | {score.items_with_deps_count} |",
        f"| Isolated Items | {score.isolated_item_count} |",
    ]
    if score.notes:
        lines.append("")
        lines.append("**Notes:**")
        for note in score.notes:
            lines.append(f"- {note}")
    return "\n".join(lines) + "\n"
