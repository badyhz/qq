# PRD Batch Planner — T876

Split waves into small batches for safer execution.

## Module

`core/prd_batch_planner.py`

## Dataclass

`PrdBatch(frozen=True)`:
- `batch_id` — unique batch identifier
- `wave_id` — parent wave
- `task_ids` — ordered task list
- `execution_order` — 0-based index
- `risk_level` — from wave
- `recommended_agent_count` — max agents for this batch
- `hard_stop_task_id` — last task in batch
- `notes` — batch notes

## Risk Rules

| Risk    | Max Agents | Notes                          |
|---------|-----------|--------------------------------|
| LOW     | wave max  |                                |
| MEDIUM  | wave max  |                                |
| HIGH    | 2         | capped regardless of wave max  |
| FROZEN  | 0         | human approval required        |

## Functions

- `plan_batches_for_wave(wave, max_tasks_per_batch=5)` — core splitter
- `batch_to_dict(batch)` / `batches_to_dict(batches)` — dict serializers
- `batch_to_markdown(batch)` / `batches_to_markdown(batches)` — markdown renderers
- `summarize_batches(batches)` — aggregate stats

## Constraints

- Pure, deterministic, no I/O, no timestamps, no random.
- Default max 5 tasks per batch.
- `hard_stop_task_id` is always last task in batch.
