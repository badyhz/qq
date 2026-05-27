# PRD 500 Backlog Materializer — T903

## Purpose

Materializes a 500+ task backlog from the domain catalog and task factory.
Pure deterministic. No I/O. No timestamps. No random.

## Module

`core/prd_500_backlog_materializer.py`

## Functions

| Function | Description |
|---|---|
| `materialize_prd_500_backlog(target_task_count=550)` | Generates tasks via factory, wraps in `PrdBacklog` |
| `materialized_500_backlog_to_dict(backlog)` | Stable dict with sorted keys |
| `summarize_prd_500_backlog(backlog)` | Summary stats dict |
| `assert_prd_500_backlog_safety(backlog)` | Returns list of safety issues (empty = safe) |

## Safety Checks

1. No title/notes contain "authorized for live trading" or "authorized for real order placement"
2. No duplicate task_ids
3. All task_ids sequential
4. FROZEN items must have status HUMAN_REVIEW_REQUIRED or BLOCKED
5. FROZEN items must have forbidden_file_patterns including "live trading" and "secrets"

## Backlog Identity

- `backlog_id`: `PRD_500_BACKLOG_V1`
- `status`: `HUMAN_REVIEW_REQUIRED`
