# PRD 500 Backlog Batch Map — T907

Splits a `PrdBacklog` into bounded batches for agent execution planning.

## Rules

- Groups items by `milestone_id`, preserves order within group.
- Each batch has at most `max_tasks_per_batch` items (default 10).
- Risk level = dominant (highest) risk in the batch: HIGH > MEDIUM > LOW > FROZEN.
- Agent count per risk: LOW/MEDIUM=8, HIGH=3, FROZEN=0.
- `hard_stop_task_id` = `end_task_id` of each batch.

## API

```python
build_prd_500_batch_map(backlog, max_tasks_per_batch=10) -> List[Prd500BatchMapEntry]
batch_map_to_dict(entry) -> dict
batch_map_to_markdown(entry) -> str
summarize_batch_map(entries) -> dict
```

## Files

- `core/prd_500_backlog_batch_map.py` — implementation
- `tests/unit/test_prd_500_backlog_batch_map.py` — tests
