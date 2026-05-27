# PRD 500 Backlog Dependency Map — T908

## Purpose

Analyzes a `PrdBacklog` for dependency issues: missing targets, cycles, future edges.

## Module

`core/prd_500_backlog_dependency_map.py`

## Dataclass

```python
@dataclass(frozen=True)
class Prd500DependencyMap:
    task_count: int
    dependency_count: int
    missing_dependency_count: int
    cycle_count: int
    future_dependency_count: int
    final_verdict: str  # PASS, WARN, BLOCKED, FAIL
    notes: List[str]
```

## Verdict Logic

| Condition | Verdict |
|---|---|
| Cycles detected | FAIL |
| Missing dependency targets | BLOCKED |
| Future deps only (dep_id > task_id) | WARN |
| No issues | PASS |

Priority: FAIL > BLOCKED > WARN > PASS.

## Functions

- `build_prd_500_dependency_map(backlog) -> Prd500DependencyMap`
- `dependency_map_to_dict(dep_map) -> dict`
- `dependency_map_to_markdown(dep_map) -> str`

## Cycle Detection

DFS-based. Counts back-edges as cycles. Uses sorted task_id iteration for determinism.

## Tests

`tests/unit/test_prd_500_backlog_dependency_map.py`

- `test_default_pass_or_warn` — no deps, verdict in {PASS, WARN}
- `test_missing_dependency_blocked` — dep target not in backlog
- `test_cycle_fail` — A->B->A cycle
- `test_deterministic` — repeated calls produce identical output
- `test_future_dep_warn` — dep_id > task_id
- `test_valid_backward_dep_pass` — dep_id < task_id
- `test_dict_keys` / `test_markdown_contains_verdict` / `test_frozen` — serializers + immutability
