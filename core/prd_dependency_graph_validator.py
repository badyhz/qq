"""PRD dependency graph validator.

T877. Pure, deterministic, no I/O, no timestamps, no random.
Validates dependencies across backlog items: missing deps, cycles, future refs.
"""

from dataclasses import dataclass
from typing import Dict, List, Set

from core.prd_backlog_schema import PrdBacklogItem


# --- Dataclasses ---


@dataclass(frozen=True)
class PrdDependencyIssue:
    issue_id: str
    severity: str  # "warning", "blocker", "fail"
    task_id: str
    dependency_id: str
    message: str


@dataclass(frozen=True)
class PrdDependencyValidationReport:
    task_count: int
    issue_count: int
    cycle_count: int
    missing_dependency_count: int
    final_verdict: str  # PASS, WARN, BLOCKED, FAIL
    issues: List[PrdDependencyIssue]
    notes: List[str]


# --- Detection functions ---


def detect_missing_dependencies(items: List[PrdBacklogItem]) -> List[PrdDependencyIssue]:
    """Find dependencies that reference task_ids not present in the item list."""
    all_ids: Set[str] = {item.task_id for item in items}
    issues: List[PrdDependencyIssue] = []
    for item in items:
        for dep_id in item.dependencies:
            if dep_id not in all_ids:
                issues.append(
                    PrdDependencyIssue(
                        issue_id=f"missing-dep-{item.task_id}-{dep_id}",
                        severity="blocker",
                        task_id=item.task_id,
                        dependency_id=dep_id,
                        message=f"Task {item.task_id} depends on {dep_id} which does not exist in backlog",
                    )
                )
    return issues


def detect_dependency_cycles(items: List[PrdBacklogItem]) -> List[PrdDependencyIssue]:
    """Detect cycles in the dependency graph using DFS."""
    adj: Dict[str, List[str]] = {item.task_id: list(item.dependencies) for item in items}
    issues: List[PrdDependencyIssue] = []
    visited: Set[str] = set()
    in_stack: Set[str] = set()
    cycle_tasks: Set[str] = set()

    def dfs(node: str, path: List[str]) -> None:
        if node in in_stack:
            # Found cycle — extract cycle path
            cycle_start = path.index(node)
            cycle_path = path[cycle_start:] + [node]
            for tid in cycle_path:
                cycle_tasks.add(tid)
            return
        if node in visited:
            return
        in_stack.add(node)
        path.append(node)
        for neighbor in adj.get(node, []):
            dfs(neighbor, path)
        path.pop()
        in_stack.discard(node)
        visited.add(node)

    for item in items:
        if item.task_id not in visited:
            dfs(item.task_id, [])

    # Deduplicate: one issue per task in a cycle
    for task_id in sorted(cycle_tasks):
        issues.append(
            PrdDependencyIssue(
                issue_id=f"cycle-{task_id}",
                severity="fail",
                task_id=task_id,
                dependency_id="",
                message=f"Task {task_id} is part of a dependency cycle",
            )
        )
    return issues


def _detect_future_dependency_warnings(items: List[PrdBacklogItem]) -> List[PrdDependencyIssue]:
    """Warn when a task depends on a higher-numbered task (future dependency)."""
    issues: List[PrdDependencyIssue] = []
    all_ids: Set[str] = {item.task_id for item in items}
    for item in items:
        for dep_id in item.dependencies:
            if dep_id in all_ids and dep_id > item.task_id:
                issues.append(
                    PrdDependencyIssue(
                        issue_id=f"future-dep-{item.task_id}-{dep_id}",
                        severity="warning",
                        task_id=item.task_id,
                        dependency_id=dep_id,
                        message=f"Task {item.task_id} depends on higher-numbered task {dep_id} (future dependency)",
                    )
                )
    return issues


# --- Main validation ---


def validate_prd_dependency_graph(items: List[PrdBacklogItem]) -> PrdDependencyValidationReport:
    """Validate dependency graph. Pure, deterministic."""
    missing = detect_missing_dependencies(items)
    cycles = detect_dependency_cycles(items)
    future_warnings = _detect_future_dependency_warnings(items)

    all_issues = missing + cycles + future_warnings

    # Determine verdict
    if cycles:
        verdict = "FAIL"
    elif missing:
        verdict = "BLOCKED"
    elif future_warnings:
        verdict = "WARN"
    else:
        verdict = "PASS"

    notes: List[str] = []
    if cycles:
        notes.append(f"Dependency cycles detected involving {len(cycles)} tasks")
    if missing:
        notes.append(f"{len(missing)} missing dependencies found")
    if future_warnings:
        notes.append(f"{len(future_warnings)} future dependency warnings")
    if not notes:
        notes.append("All dependencies valid")

    return PrdDependencyValidationReport(
        task_count=len(items),
        issue_count=len(all_issues),
        cycle_count=len(cycles),
        missing_dependency_count=len(missing),
        final_verdict=verdict,
        issues=tuple(all_issues),  # type: ignore[arg-type]
        notes=tuple(notes),  # type: ignore[arg-type]
    )


# --- Serializers ---


def dependency_report_to_dict(report: PrdDependencyValidationReport) -> Dict:
    """Convert report to plain dict."""
    return {
        "task_count": report.task_count,
        "issue_count": report.issue_count,
        "cycle_count": report.cycle_count,
        "missing_dependency_count": report.missing_dependency_count,
        "final_verdict": report.final_verdict,
        "issues": [
            {
                "issue_id": i.issue_id,
                "severity": i.severity,
                "task_id": i.task_id,
                "dependency_id": i.dependency_id,
                "message": i.message,
            }
            for i in report.issues
        ],
        "notes": list(report.notes),
    }


def dependency_report_to_markdown(report: PrdDependencyValidationReport) -> str:
    """Convert report to markdown string."""
    lines: List[str] = []
    lines.append("# PRD Dependency Validation Report")
    lines.append("")
    lines.append(f"- **Tasks:** {report.task_count}")
    lines.append(f"- **Issues:** {report.issue_count}")
    lines.append(f"- **Cycles:** {report.cycle_count}")
    lines.append(f"- **Missing deps:** {report.missing_dependency_count}")
    lines.append(f"- **Verdict:** {report.final_verdict}")
    lines.append("")
    if report.notes:
        lines.append("## Notes")
        for note in report.notes:
            lines.append(f"- {note}")
        lines.append("")
    if report.issues:
        lines.append("## Issues")
        lines.append("")
        lines.append("| ID | Severity | Task | Dependency | Message |")
        lines.append("|---|---|---|---|---|")
        for issue in report.issues:
            lines.append(
                f"| {issue.issue_id} | {issue.severity} | {issue.task_id} | "
                f"{issue.dependency_id} | {issue.message} |"
            )
        lines.append("")
    return "\n".join(lines)
