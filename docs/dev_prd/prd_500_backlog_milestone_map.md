# PRD 500 Backlog Milestone Map

T905. Pure deterministic module for grouping 500+ backlog items by milestone.

## Purpose

Aggregate a `PrdBacklog` into per-milestone summaries: task range, count, highest risk, aggregate status, human-review flag.

## Module

`core/prd_500_backlog_milestone_map.py`

### Dataclass

`Prd500MilestoneMapEntry` (frozen):
- `milestone_id`, `title`, `start_task_id`, `end_task_id`
- `task_count`, `risk_level`, `status`
- `human_review_required` (bool), `notes`

### Functions

| Function | Input | Output |
|---|---|---|
| `build_prd_500_milestone_map` | `PrdBacklog` | `List[Prd500MilestoneMapEntry]` |
| `milestone_map_to_dict` | entry | `dict` |
| `milestone_map_to_markdown` | entry | `str` |
| `summarize_milestone_map` | entries | `dict` |

## Rules

- Group by `milestone_id`, preserve first-seen order.
- `risk_level` = highest in group: FROZEN > HIGH > MEDIUM > LOW.
- `human_review_required` = True if any item FROZEN or HIGH.
- `status` priority: BLOCKED > IN_PROGRESS > HUMAN_REVIEW_REQUIRED > PARTIAL > NOT_STARTED > COMPLETED.
- Notes merged with dedup, preserving insertion order.

## Tests

`tests/unit/test_prd_500_backlog_milestone_map.py` — coverage: ordering, risk aggregation, human review flag, determinism, status derivation, note dedup, serializers.
