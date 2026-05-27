"""PRD 500 backlog execution windows — deterministic window splitting.

T910. Pure deterministic. No I/O. No timestamps. No random.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem

# --- Dataclass ---


@dataclass(frozen=True)
class Prd500ExecutionWindow:
    window_id: str
    start_task_id: str
    end_task_id: str
    task_count: int
    risk_level: str
    recommended_route: str
    max_parallel_agents: int
    hard_stop_task_id: str
    human_review_required: bool
    notes: List[str]


# --- Constants ---

# Window size ranges by risk level
_WINDOW_SIZE = {
    "LOW": (20, 50),
    "MEDIUM": (20, 50),
    "HIGH": (3, 15),
    "FROZEN": (0, 0),
}

# Max parallel agents by risk level
_MAX_PARALLEL = {
    "LOW": 8,
    "MEDIUM": 6,
    "HIGH": 3,
    "FROZEN": 0,
}

# Recommended route by risk level
_ROUTE_MAP = {
    "FROZEN": "HUMAN_ONLY",
    "HIGH": "mimo2.5pro with human review",
    "MEDIUM": "mimo2.5pro",
    "LOW": "mimo2.5pro or mimo2.5",
}


# --- Helpers ---


def _determine_dominant_risk(items: List[PrdBacklogItem]) -> str:
    """Highest risk wins. FROZEN > HIGH > MEDIUM > LOW."""
    risk_priority = {"FROZEN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    if not items:
        return "LOW"
    dominant = max(risk_priority.get(it.risk_level, 0) for it in items)
    return next(k for k, v in risk_priority.items() if v == dominant)


def _target_window_size(risk_level: str) -> int:
    """Return the upper bound of the window size range for a risk level."""
    _, upper = _WINDOW_SIZE.get(risk_level, (20, 50))
    return upper


# --- Builder ---


def build_prd_500_execution_windows(
    backlog: PrdBacklog,
) -> List[Prd500ExecutionWindow]:
    """Split backlog into execution windows grouped by milestone_id.

    Each window respects risk-based size limits.
    FROZEN items produce windows with 0 executable tasks and human_review_required=True.
    Preserves original item order within each milestone group.
    """
    # Group by milestone_id, preserving order
    milestone_groups: Dict[str, List[PrdBacklogItem]] = {}
    milestone_order: List[str] = []
    for item in backlog.items:
        if item.milestone_id not in milestone_groups:
            milestone_groups[item.milestone_id] = []
            milestone_order.append(item.milestone_id)
        milestone_groups[item.milestone_id].append(item)

    windows: List[Prd500ExecutionWindow] = []
    global_window_idx = 0

    for milestone_id in milestone_order:
        items = milestone_groups[milestone_id]
        dominant_risk = _determine_dominant_risk(items)
        max_win_size = _target_window_size(dominant_risk)

        # FROZEN: single window, 0 executable tasks
        if dominant_risk == "FROZEN":
            global_window_idx += 1
            notes: List[str] = []
            notes.append(f"milestone {milestone_id}: all items FROZEN, no executable tasks")
            win = Prd500ExecutionWindow(
                window_id=f"W{global_window_idx:04d}",
                start_task_id=items[0].task_id,
                end_task_id=items[-1].task_id,
                task_count=0,
                risk_level="FROZEN",
                recommended_route=_ROUTE_MAP["FROZEN"],
                max_parallel_agents=0,
                hard_stop_task_id=items[-1].task_id,
                human_review_required=True,
                notes=notes,
            )
            windows.append(win)
            continue

        # Split into chunks
        for chunk_start in range(0, len(items), max_win_size):
            chunk = items[chunk_start : chunk_start + max_win_size]
            global_window_idx += 1
            chunk_risk = _determine_dominant_risk(chunk)
            win_notes: List[str] = []

            is_frozen = chunk_risk == "FROZEN"
            if is_frozen:
                win_notes.append("chunk contains FROZEN items, no executable tasks")

            win = Prd500ExecutionWindow(
                window_id=f"W{global_window_idx:04d}",
                start_task_id=chunk[0].task_id,
                end_task_id=chunk[-1].task_id,
                task_count=0 if is_frozen else len(chunk),
                risk_level=chunk_risk,
                recommended_route=_ROUTE_MAP.get(chunk_risk, "mimo2.5pro"),
                max_parallel_agents=_MAX_PARALLEL.get(chunk_risk, 0),
                hard_stop_task_id=chunk[-1].task_id,
                human_review_required=is_frozen or chunk_risk == "HIGH",
                notes=win_notes,
            )
            windows.append(win)

    return windows


# --- Serializers ---


def execution_windows_to_dict(window: Prd500ExecutionWindow) -> Dict[str, Any]:
    """Convert window to dict. Pure."""
    return {
        "window_id": window.window_id,
        "start_task_id": window.start_task_id,
        "end_task_id": window.end_task_id,
        "task_count": window.task_count,
        "risk_level": window.risk_level,
        "recommended_route": window.recommended_route,
        "max_parallel_agents": window.max_parallel_agents,
        "hard_stop_task_id": window.hard_stop_task_id,
        "human_review_required": window.human_review_required,
        "notes": list(window.notes),
    }


def execution_windows_to_markdown(window: Prd500ExecutionWindow) -> str:
    """Convert window to markdown. Pure."""
    lines: List[str] = []
    lines.append(f"### Window {window.window_id}")
    lines.append("")
    lines.append(f"- **Tasks:** {window.start_task_id} .. {window.end_task_id} ({window.task_count})")
    lines.append(f"- **Risk:** {window.risk_level}")
    lines.append(f"- **Route:** {window.recommended_route}")
    lines.append(f"- **Max parallel agents:** {window.max_parallel_agents}")
    lines.append(f"- **Hard stop:** {window.hard_stop_task_id}")
    lines.append(f"- **Human review required:** {window.human_review_required}")
    if window.notes:
        lines.append("- **Notes:**")
        for note in window.notes:
            lines.append(f"  - {note}")
    lines.append("")
    return "\n".join(lines)


# --- Summary ---


def summarize_execution_windows(windows: List[Prd500ExecutionWindow]) -> Dict[str, Any]:
    """Summarize execution windows. Pure."""
    total_tasks = sum(w.task_count for w in windows)
    risk_counts: Dict[str, int] = {}
    for w in windows:
        risk_counts[w.risk_level] = risk_counts.get(w.risk_level, 0) + 1
    human_review_count = sum(1 for w in windows if w.human_review_required)
    return {
        "total_windows": len(windows),
        "total_executable_tasks": total_tasks,
        "risk_counts": risk_counts,
        "human_review_required_count": human_review_count,
        "max_window_size": max((w.task_count for w in windows), default=0),
    }
