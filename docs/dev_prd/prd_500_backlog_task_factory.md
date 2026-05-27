# T902 — PRD 500 Backlog Task Factory

## Purpose

Deterministic task factory that generates 550+ `PrdBacklogItem` tasks from the domain catalog (T901). No I/O. No timestamps. No random.

## Module

`core/prd_500_backlog_task_factory.py`

## Key Types

- `Prd500TaskFactoryConfig` — frozen dataclass: start_task_number, target_task_count, default_status, notes
- `generate_prd_500_backlog_tasks()` — main entry point, iterates domains, returns `List[PrdBacklogItem]`
- `generate_tasks_for_domain()` — generates N tasks for one domain
- `summarize_generated_tasks()` — returns summary dict

## Rules

- Task IDs: sequential T901, T902, T903, ...
- Title: `{domain.title} -- task {N}`
- FROZEN domains: status=`HUMAN_REVIEW_REQUIRED`, no acceptance commands
- Non-frozen: status=`NOT_STARTED`, acceptance=`["pytest"]`
- Dependencies: each task depends on previous in same domain (first has none)
- No task may contain "authorized for live trading" or "authorized for real order placement"

## Test

```
python3 -m pytest tests/unit/test_prd_500_backlog_task_factory.py -q
```
