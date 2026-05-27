# PRD Dependency Graph Validator — T877

Validates dependency relationships across PRD backlog items.

## Dataclasses

### PrdDependencyIssue (frozen)
Single validation issue with `issue_id`, `severity` (warning/blocker/fail), `task_id`, `dependency_id`, `message`.

### PrdDependencyValidationReport (frozen)
Aggregated report: `task_count`, `issue_count`, `cycle_count`, `missing_dependency_count`, `final_verdict`, `issues`, `notes`.

## Functions

| Function | Purpose |
|---|---|
| `validate_prd_dependency_graph(items)` | Main entry. Returns `PrdDependencyValidationReport`. |
| `detect_missing_dependencies(items)` | Returns issues for deps pointing to nonexistent task_ids. |
| `detect_dependency_cycles(items)` | DFS-based cycle detection. Returns issues for tasks in cycles. |
| `dependency_report_to_dict(report)` | Serialize report to plain dict. |
| `dependency_report_to_markdown(report)` | Serialize report to markdown table. |

## Verdict rules

| Condition | Verdict |
|---|---|
| No issues | PASS |
| Warnings only | WARN |
| Any missing dependency | BLOCKED |
| Any cycle | FAIL |

Precedence: FAIL > BLOCKED > WARN > PASS.

## Constraints

- Pure, deterministic, no I/O, no timestamps, no random.
- Imports `PrdBacklogItem` from `core.prd_backlog_schema` (unchanged).
