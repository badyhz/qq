"""PRD 500 backlog dependency map — T908.

Builds a dependency map from a PrdBacklog: counts, missing deps, cycles,
future deps. Pure deterministic, no I/O, no timestamps, no random.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem


# --- Dataclass ---


@dataclass(frozen=True)
class Prd500DependencyMap:
    task_count: int
    dependency_count: int
    missing_dependency_count: int
    cycle_count: int
    future_dependency_count: int
    final_verdict: str  # PASS, WARN, BLOCKED, FAIL
    notes: List[str]


# --- Cycle detection (DFS) ---


def _detect_cycles(task_ids: Set[str], adj: Dict[str, List[str]]) -> int:
    """Count distinct cycles via DFS. Returns cycle count."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {tid: WHITE for tid in task_ids}
    cycle_count = 0

    def dfs(node: str) -> None:
        nonlocal cycle_count
        color[node] = GRAY
        for neighbor in adj.get(node, []):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                cycle_count += 1
            elif color[neighbor] == WHITE:
                dfs(neighbor)
        color[node] = BLACK

    for tid in sorted(task_ids):
        if color[tid] == WHITE:
            dfs(tid)

    return cycle_count


# --- Core logic ---


def build_prd_500_dependency_map(backlog: PrdBacklog) -> Prd500DependencyMap:
    """Build dependency map from a PrdBacklog. Pure deterministic."""
    task_ids: Set[str] = {item.task_id for item in backlog.items}
    notes: List[str] = []

    # Count dependencies and check missing / future
    dep_count = 0
    missing_deps: List[str] = []
    future_deps: List[str] = []

    # Build adjacency list for cycle detection
    adj: Dict[str, List[str]] = {tid: [] for tid in task_ids}

    for item in backlog.items:
        for dep_id in item.dependencies:
            dep_count += 1
            if dep_id not in task_ids:
                missing_deps.append(f"{item.task_id}->{dep_id}")
            else:
                adj[item.task_id].append(dep_id)
                if dep_id > item.task_id:
                    future_deps.append(f"{item.task_id}->{dep_id}")

    cycle_count = _detect_cycles(task_ids, adj)

    # Verdict logic
    if cycle_count > 0:
        verdict = "FAIL"
        notes.append(f"{cycle_count} cycle(s) detected")
    elif missing_deps:
        verdict = "BLOCKED"
        notes.append(f"{len(missing_deps)} missing dependency target(s)")
    elif future_deps:
        verdict = "WARN"
        notes.append(f"{len(future_deps)} future dependency edge(s)")
    else:
        verdict = "PASS"

    if not notes:
        notes.append("no issues")

    return Prd500DependencyMap(
        task_count=len(task_ids),
        dependency_count=dep_count,
        missing_dependency_count=len(missing_deps),
        cycle_count=cycle_count,
        future_dependency_count=len(future_deps),
        final_verdict=verdict,
        notes=notes,
    )


# --- Serializers ---


def dependency_map_to_dict(dep_map: Prd500DependencyMap) -> Dict[str, object]:
    """Convert Prd500DependencyMap to plain dict."""
    return {
        "task_count": dep_map.task_count,
        "dependency_count": dep_map.dependency_count,
        "missing_dependency_count": dep_map.missing_dependency_count,
        "cycle_count": dep_map.cycle_count,
        "future_dependency_count": dep_map.future_dependency_count,
        "final_verdict": dep_map.final_verdict,
        "notes": list(dep_map.notes),
    }


def dependency_map_to_markdown(dep_map: Prd500DependencyMap) -> str:
    """Convert Prd500DependencyMap to markdown string."""
    lines: List[str] = []
    lines.append("# PRD 500 Backlog Dependency Map")
    lines.append("")
    lines.append(f"- **Task count:** {dep_map.task_count}")
    lines.append(f"- **Dependency edges:** {dep_map.dependency_count}")
    lines.append(f"- **Missing dependencies:** {dep_map.missing_dependency_count}")
    lines.append(f"- **Cycles:** {dep_map.cycle_count}")
    lines.append(f"- **Future dependencies:** {dep_map.future_dependency_count}")
    lines.append(f"- **Verdict:** {dep_map.final_verdict}")
    lines.append("")
    if dep_map.notes:
        lines.append("## Notes")
        lines.append("")
        for note in dep_map.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
