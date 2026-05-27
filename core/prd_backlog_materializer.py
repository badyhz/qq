"""PRD backlog materializer — T889.

Converts milestone seed objects into a full PrdBacklog with frozen guard.
Pure deterministic, no I/O, no timestamps, no random.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_backlog_frozen_milestone_guard import (
    PrdFrozenMilestoneGuard,
    check_frozen_milestone,
)
from core.prd_backlog_schema import (
    PrdBacklog,
    PrdBacklogItem,
    backlog_to_dict,
    backlog_to_markdown,
    backlog_item_to_dict,
    backlog_item_to_markdown,
    build_backlog_item,
)


# --- Dataclasses ---


@dataclass(frozen=True)
class PrdMaterializationResult:
    backlog: PrdBacklog
    materialized_count: int
    milestone_count: int
    frozen_guard: PrdFrozenMilestoneGuard
    notes: tuple


# --- Core logic ---


def _build_item_from_seed_dict(
    task_dict: Dict[str, Any],
    milestone_id: str,
    wave_id: str,
    batch_id: str,
) -> PrdBacklogItem:
    """Convert a seed task dict into a PrdBacklogItem.

    Fills defaults for optional fields not present in seed dicts.
    """
    return build_backlog_item(
        task_id=task_dict["task_id"],
        title=task_dict["title"],
        milestone_id=milestone_id,
        wave_id=wave_id,
        batch_id=batch_id,
        risk_level=task_dict.get("risk_level", "LOW"),
        status=task_dict.get("status", "NOT_STARTED"),
        dependencies=task_dict.get("dependencies", []),
        allowed_file_patterns=task_dict.get("allowed_file_patterns", []),
        forbidden_file_patterns=task_dict.get("forbidden_file_patterns", []),
        acceptance_command_ids=task_dict.get("acceptance_command_ids", []),
        notes=task_dict.get("notes", []),
    )


def materialize_backlog_from_seeds(
    milestone_seeds: list,
    target_count: int = 500,
) -> PrdMaterializationResult:
    """Materialize a full PrdBacklog from milestone seed objects.

    Each seed must have attributes: milestone_id (str), task_items (list of dicts).
    Each task_item dict must have at least: task_id, title.
    Optional: status, risk_level, dependencies.

    Wave and batch IDs are auto-assigned:
      wave_id  = milestone_id + "-W0"
      batch_id = wave_id + "-B0"
    """
    all_items: List[PrdBacklogItem] = []
    notes: List[str] = []

    for seed in milestone_seeds:
        mid = seed.milestone_id
        wave_id = mid + "-W0"
        batch_id = wave_id + "-B0"

        for task_dict in seed.task_items:
            item = _build_item_from_seed_dict(
                task_dict=task_dict,
                milestone_id=mid,
                wave_id=wave_id,
                batch_id=batch_id,
            )
            all_items.append(item)

        notes.append(
            f"Materialized {len(seed.task_items)} tasks from {mid} "
            f"({getattr(seed, 'title', 'untitled')})"
        )

    frozen_guard = check_frozen_milestone(all_items)

    status = "MATERIALIZED"
    if frozen_guard.verdict == "BLOCKED":
        status = "FROZEN_GUARD_BLOCKED"

    backlog = PrdBacklog(
        backlog_id="BACKLOG-MATERIALIZED",
        items=all_items,
        total_expected_tasks=target_count,
        status=status,
        notes=list(notes),
    )

    return PrdMaterializationResult(
        backlog=backlog,
        materialized_count=len(all_items),
        milestone_count=len(milestone_seeds),
        frozen_guard=frozen_guard,
        notes=tuple(notes),
    )


def materialize_default_backlog() -> PrdMaterializationResult:
    """Import all 7 milestone seed factories and build the default backlog."""
    from core.prd_backlog_milestone1_seed import build_milestone1_seed
    from core.prd_backlog_milestone2_seed import build_milestone2_seed
    from core.prd_backlog_milestone3_seed import build_milestone3_seed
    from core.prd_backlog_milestone4_seed import build_milestone4_seed
    from core.prd_backlog_milestone5_seed import build_milestone5_seed
    from core.prd_backlog_milestone6_seed import build_milestone6_seed
    from core.prd_backlog_milestone7_seed import build_milestone7_seed

    seeds = [
        build_milestone1_seed(),
        build_milestone2_seed(),
        build_milestone3_seed(),
        build_milestone4_seed(),
        build_milestone5_seed(),
        build_milestone6_seed(),
        build_milestone7_seed(),
    ]
    return materialize_backlog_from_seeds(seeds)


# --- Serializers ---


def materialization_result_to_dict(result: PrdMaterializationResult) -> Dict[str, Any]:
    """Convert PrdMaterializationResult to plain dict."""
    from core.prd_backlog_frozen_milestone_guard import frozen_guard_to_dict

    return {
        "backlog": backlog_to_dict(result.backlog),
        "materialized_count": result.materialized_count,
        "milestone_count": result.milestone_count,
        "frozen_guard": frozen_guard_to_dict(result.frozen_guard),
        "notes": list(result.notes),
    }


def materialization_result_to_markdown(result: PrdMaterializationResult) -> str:
    """Convert PrdMaterializationResult to markdown string."""
    from core.prd_backlog_frozen_milestone_guard import frozen_guard_to_markdown

    lines: List[str] = []
    lines.append("# PRD Materialization Result")
    lines.append("")
    lines.append(f"- **Materialized tasks:** {result.materialized_count}")
    lines.append(f"- **Milestone count:** {result.milestone_count}")
    lines.append("")
    lines.append("## Frozen Guard")
    lines.append("")
    lines.append(frozen_guard_to_markdown(result.frozen_guard))
    lines.append("")
    lines.append("## Backlog")
    lines.append("")
    lines.append(backlog_to_markdown(result.backlog))
    return "\n".join(lines)
