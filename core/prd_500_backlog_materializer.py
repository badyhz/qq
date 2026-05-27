"""T903 — 500 backlog materializer.

Deterministic. No I/O. No timestamps. No random.
"""

from typing import List

from core.prd_backlog_schema import (
    PrdBacklog,
    PrdBacklogItem,
    backlog_to_dict,
    build_backlog_item,
    summarize_backlog,
)
from core.prd_500_backlog_task_factory import generate_prd_500_backlog_tasks

# --- Constants ---

BACKLOG_ID = "PRD_500_BACKLOG_V1"

_BACKLOG_NOTES = [
    "500+ task backlog materialized",
    "frozen domain present",
    "human review required before execution",
]

_FORBIDDEN_PHRASES = frozenset({
    "authorized for live trading",
    "authorized for real order placement",
})

_FROZEN_SAFE_STATUSES = frozenset({
    "HUMAN_REVIEW_REQUIRED",
    "BLOCKED",
})

_FROZEN_REQUIRED_FORBIDDEN_PATTERNS = frozenset({
    "live trading",
    "secrets",
})


# --- Materializer ---


def materialize_prd_500_backlog(target_task_count: int = 550) -> PrdBacklog:
    """Generate and wrap tasks into a PrdBacklog.

    Pure deterministic. No I/O. No timestamps. No random.
    """
    if target_task_count < 1:
        raise ValueError(f"target_task_count must be >= 1, got {target_task_count}")

    items = generate_prd_500_backlog_tasks(target_task_count=target_task_count)

    return PrdBacklog(
        backlog_id=BACKLOG_ID,
        items=items,
        total_expected_tasks=target_task_count,
        status="HUMAN_REVIEW_REQUIRED",
        notes=list(_BACKLOG_NOTES),
    )


# --- Serializers ---


def materialized_500_backlog_to_dict(backlog: PrdBacklog) -> dict:
    """Stable dict with sorted keys."""
    raw = backlog_to_dict(backlog)
    return dict(sorted(raw.items()))


# --- Summary ---


def summarize_prd_500_backlog(backlog: PrdBacklog) -> dict:
    """Summary stats for the materialized backlog."""
    return summarize_backlog(backlog)


# --- Safety ---


def assert_prd_500_backlog_safety(backlog: PrdBacklog) -> List[str]:
    """Return list of safety issues. Empty list = safe.

    Checks:
    1. No item title/notes contain forbidden authorization phrases.
    2. No duplicate task_ids.
    3. All task_ids sequential (T901, T902, ...).
    4. FROZEN risk items have status HUMAN_REVIEW_REQUIRED or BLOCKED.
    5. FROZEN items have forbidden_file_patterns including 'live trading' and 'secrets'.
    """
    issues: List[str] = []

    seen_ids: set = set()
    task_numbers: List[int] = []

    for item in backlog.items:
        # 1. Forbidden phrases
        lower_title = item.title.lower()
        for phrase in _FORBIDDEN_PHRASES:
            if phrase in lower_title:
                issues.append(
                    f"{item.task_id}: title contains forbidden phrase '{phrase}'"
                )

        for note in item.notes:
            lower_note = note.lower()
            for phrase in _FORBIDDEN_PHRASES:
                if phrase in lower_note:
                    issues.append(
                        f"{item.task_id}: note contains forbidden phrase '{phrase}'"
                    )

        # 2. Duplicate task_ids
        if item.task_id in seen_ids:
            issues.append(f"Duplicate task_id: {item.task_id}")
        seen_ids.add(item.task_id)

        # 3. Track task numbers for sequential check
        num = int(item.task_id[1:])
        task_numbers.append(num)

        # 4. FROZEN status check
        if item.risk_level == "FROZEN":
            if item.status not in _FROZEN_SAFE_STATUSES:
                issues.append(
                    f"{item.task_id}: FROZEN item has status '{item.status}', "
                    f"expected one of {sorted(_FROZEN_SAFE_STATUSES)}"
                )

            # 5. FROZEN forbidden patterns
            lower_patterns = {p.lower() for p in item.forbidden_file_patterns}
            for required in _FROZEN_REQUIRED_FORBIDDEN_PATTERNS:
                if not any(required in pat for pat in lower_patterns):
                    issues.append(
                        f"{item.task_id}: FROZEN item missing forbidden pattern '{required}'"
                    )

    # 3. Sequential check
    if task_numbers:
        expected_start = task_numbers[0]
        for i, num in enumerate(task_numbers):
            expected = expected_start + i
            if num != expected:
                issues.append(
                    f"Non-sequential task_id: expected T{expected}, got T{num}"
                )
                break

    return issues
