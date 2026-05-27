"""PRD 500 backlog milestone map — group backlog items by milestone.

T905. Pure deterministic. No I/O. No timestamps. No random.
"""

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem

# risk severity: higher index = higher severity
_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "FROZEN": 3}


@dataclass(frozen=True)
class Prd500MilestoneMapEntry:
    milestone_id: str
    title: str
    start_task_id: str
    end_task_id: str
    task_count: int
    risk_level: str
    status: str
    human_review_required: bool
    notes: List[str]


def _highest_risk(items: List[PrdBacklogItem]) -> str:
    """Return highest risk level among items. Deterministic."""
    best = "LOW"
    for item in items:
        if _RISK_ORDER.get(item.risk_level, 0) > _RISK_ORDER.get(best, 0):
            best = item.risk_level
    return best


def _needs_human_review(items: List[PrdBacklogItem]) -> bool:
    """True if any item is FROZEN or HIGH."""
    for item in items:
        if item.risk_level in ("FROZEN", "HIGH"):
            return True
    return False


def _derive_status(items: List[PrdBacklogItem]) -> str:
    """Derive aggregate status for a milestone group."""
    statuses = {item.status for item in items}
    if statuses == {"COMPLETED"}:
        return "COMPLETED"
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if "IN_PROGRESS" in statuses:
        return "IN_PROGRESS"
    if "HUMAN_REVIEW_REQUIRED" in statuses:
        return "HUMAN_REVIEW_REQUIRED"
    if "PARTIAL" in statuses:
        return "PARTIAL"
    return "NOT_STARTED"


def build_prd_500_milestone_map(backlog: PrdBacklog) -> List[Prd500MilestoneMapEntry]:
    """Group backlog items by milestone_id, preserve order, compute aggregates.

    Returns list sorted by first task_id appearance in backlog.
    """
    # group preserving insertion order
    groups: OrderedDict[str, List[PrdBacklogItem]] = OrderedDict()
    for item in backlog.items:
        groups.setdefault(item.milestone_id, []).append(item)

    entries: List[Prd500MilestoneMapEntry] = []
    for milestone_id, items in groups.items():
        task_ids = [it.task_id for it in items]
        merged_notes: List[str] = []
        seen: set = set()
        for it in items:
            for note in it.notes:
                if note not in seen:
                    seen.add(note)
                    merged_notes.append(note)
        entries.append(
            Prd500MilestoneMapEntry(
                milestone_id=milestone_id,
                title=milestone_id,
                start_task_id=task_ids[0],
                end_task_id=task_ids[-1],
                task_count=len(items),
                risk_level=_highest_risk(items),
                status=_derive_status(items),
                human_review_required=_needs_human_review(items),
                notes=merged_notes,
            )
        )
    return entries


def milestone_map_to_dict(entry: Prd500MilestoneMapEntry) -> Dict[str, Any]:
    """Serialize one entry to dict."""
    return {
        "milestone_id": entry.milestone_id,
        "title": entry.title,
        "start_task_id": entry.start_task_id,
        "end_task_id": entry.end_task_id,
        "task_count": entry.task_count,
        "risk_level": entry.risk_level,
        "status": entry.status,
        "human_review_required": entry.human_review_required,
        "notes": list(entry.notes),
    }


def milestone_map_to_markdown(entry: Prd500MilestoneMapEntry) -> str:
    """Render one entry as markdown."""
    lines: List[str] = []
    lines.append(f"## {entry.milestone_id}: {entry.title}")
    lines.append("")
    lines.append(f"- **Tasks:** {entry.start_task_id} .. {entry.end_task_id} ({entry.task_count})")
    lines.append(f"- **Risk:** {entry.risk_level}")
    lines.append(f"- **Status:** {entry.status}")
    lines.append(f"- **Human review:** {'YES' if entry.human_review_required else 'no'}")
    if entry.notes:
        lines.append("- **Notes:**")
        for note in entry.notes:
            lines.append(f"  - {note}")
    lines.append("")
    return "\n".join(lines)


def summarize_milestone_map(entries: List[Prd500MilestoneMapEntry]) -> Dict[str, Any]:
    """Aggregate summary across all milestone entries."""
    total_tasks = sum(e.task_count for e in entries)
    risk_counts: Dict[str, int] = {}
    status_counts: Dict[str, int] = {}
    human_review_count = 0
    for e in entries:
        risk_counts[e.risk_level] = risk_counts.get(e.risk_level, 0) + 1
        status_counts[e.status] = status_counts.get(e.status, 0) + 1
        if e.human_review_required:
            human_review_count += 1
    return {
        "milestone_count": len(entries),
        "total_tasks": total_tasks,
        "risk_counts": risk_counts,
        "status_counts": status_counts,
        "human_review_required_count": human_review_count,
    }
