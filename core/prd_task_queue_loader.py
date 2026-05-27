"""PRD task queue loader — parse task queue from markdown text.

T866. Pure deterministic, no I/O, no timestamps, no random.
"""

import re
from typing import Any, Dict, List

from core.prd_task_model import PrdTask, validate_task_id

# --- Constants ---

_TASK_ID_RE = re.compile(r"\b(T\d+)\b")
_RANGE_RE = re.compile(r"\b(T\d+)\s*[-–—]\s*(T\d+)\b")
_COMPLETED_RE = re.compile(r"\bcompleted\b", re.IGNORECASE)


# --- Public API ---


def load_prd_task_queue_from_markdown(markdown_text: str) -> List[PrdTask]:
    """Load PrdTask objects from markdown text.

    Deduplicates by task_id (first occurrence wins).
    Produces minimal PrdTask objects from line-level extraction.
    """
    seen: set = set()
    tasks: List[PrdTask] = []

    for line in markdown_text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check for range (e.g. T786-T789: description — completed)
        range_match = _RANGE_RE.search(line_stripped)
        if range_match:
            start_id = range_match.group(1)
            end_id = range_match.group(2)
            start_num = int(start_id[1:])
            end_num = int(end_id[1:])
            # Extract title after the range
            colon_pos = line_stripped.find(":", range_match.end())
            title_part = line_stripped[colon_pos + 1 :].strip() if colon_pos != -1 else ""
            # Strip trailing status markers
            title_part = re.split(r"\s*[-–—]\s*$", title_part)[0].strip()
            # Clean trailing status words
            title_part = re.sub(r"\s*(completed|in_progress|NOT_STARTED)\s*$", "", title_part, flags=re.IGNORECASE).strip()
            status = "COMPLETED" if _COMPLETED_RE.search(line_stripped) else "NOT_STARTED"
            for num in range(start_num, end_num + 1):
                tid = f"T{num}"
                if tid in seen:
                    continue
                seen.add(tid)
                tasks.append(_make_task(tid, title_part, status))
            continue

        # Check for single task ID
        task_match = _TASK_ID_RE.search(line_stripped)
        if task_match:
            tid = task_match.group(1)
            if tid in seen:
                continue
            seen.add(tid)
            rest = line_stripped[task_match.end() :]
            colon_pos = rest.find(":")
            if colon_pos != -1:
                # Colon-delimited: "T865: title text"
                title_part = rest[colon_pos + 1 :].strip()
            elif "|" in rest:
                # Table row: "| T900 | some title | status |"
                cells = [c.strip() for c in rest.split("|") if c.strip()]
                title_part = cells[0] if cells else ""
            else:
                title_part = ""
            # Clean trailing status words
            title_part = re.sub(r"\s*(completed|in_progress|NOT_STARTED|HUMAN_REVIEW_REQUIRED)\s*$", "", title_part, flags=re.IGNORECASE).strip()
            status = "COMPLETED" if _COMPLETED_RE.search(line_stripped) else "NOT_STARTED"
            tasks.append(_make_task(tid, title_part, status))

    return tasks


def extract_task_ids_from_markdown(markdown_text: str) -> List[str]:
    """Extract unique task IDs from markdown text, preserving order."""
    seen: set = set()
    result: List[str] = []
    for match in _TASK_ID_RE.finditer(markdown_text):
        tid = match.group(1)
        if tid not in seen:
            seen.add(tid)
            result.append(tid)
    return result


def find_task_section(markdown_text: str, task_id: str) -> str:
    """Find the markdown section containing a task_id.

    Returns the block of text from the nearest preceding ## heading
    through the next ## heading (exclusive). Returns "" if not found.
    """
    if not validate_task_id(task_id):
        return ""

    lines = markdown_text.splitlines()
    # Find which line contains the task_id
    target_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"\b" + re.escape(task_id) + r"\b", line):
            target_idx = i
            break

    if target_idx == -1:
        return ""

    # Walk backwards to find preceding ## heading
    section_start = 0
    for i in range(target_idx - 1, -1, -1):
        if lines[i].startswith("## "):
            section_start = i
            break

    # Walk forwards to find next ## heading
    section_end = len(lines)
    for i in range(target_idx + 1, len(lines)):
        if lines[i].startswith("## "):
            section_end = i
            break

    return "\n".join(lines[section_start:section_end])


def task_queue_loader_summary(tasks: List[PrdTask]) -> Dict[str, Any]:
    """Produce summary dict from a list of PrdTask objects."""
    status_counts: Dict[str, int] = {}
    risk_counts: Dict[str, int] = {}
    for t in tasks:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1
        risk_counts[t.risk_level] = risk_counts.get(t.risk_level, 0) + 1
    return {
        "total": len(tasks),
        "task_ids": [t.task_id for t in tasks],
        "status_counts": status_counts,
        "risk_counts": risk_counts,
    }


# --- Internal ---


def _make_task(task_id: str, title: str, status: str) -> PrdTask:
    return PrdTask(
        task_id=task_id,
        title=title,
        status=status,
        allowed_files=[],
        dependencies=[],
        acceptance_commands=[],
        risk_level="MEDIUM",
        notes=["loaded_from_markdown"],
    )
