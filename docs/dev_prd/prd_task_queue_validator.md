# PRD Task Queue Validator — T867

## Purpose

Validate PRD task queue ranges and safety before execution.

## Module

`core/prd_task_queue_validator.py`

Pure, deterministic. No I/O, no timestamps, no random.

## Dataclasses

### PrdTaskValidationIssue (frozen=True)

| Field      | Type  | Values                        |
|------------|-------|-------------------------------|
| issue_id   | str   | Auto-generated                |
| task_id    | str   | Related task                  |
| severity   | str   | blocker, warning              |
| message    | str   | Human-readable                |
| category   | str   | Classification                |

### PrdTaskQueueValidationReport (frozen=True)

| Field         | Type                              |
|---------------|-----------------------------------|
| total_tasks   | int                               |
| issue_count   | int                               |
| blocker_count | int                               |
| warning_count | int                               |
| final_verdict | str (PASS/WARN/BLOCKED/FAIL)      |
| issues        | tuple[PrdTaskValidationIssue, ...]|
| notes         | tuple[str, ...]                   |

## Validation Rules

1. **Task ID format** — all IDs must match `T<digits>` (blocker → FAIL if any invalid)
2. **No duplicates** — each task ID appears once (blocker)
3. **Range present** — start and end IDs exist in task list (blocker)
4. **Range order** — start numeric <= end numeric (blocker)
5. **Status valid** — must be in `VALID_STATUSES` (blocker)
6. **Risk level valid** — must be in `VALID_RISK_LEVELS` (blocker)
7. **Forbidden statuses** — `HUMAN_REVIEW_REQUIRED`, `FROZEN` must not auto-execute (warning)
8. **Contiguity** — gaps in numeric range produce notes (not issues)

## Final Verdict

| Verdict  | Condition                              |
|----------|----------------------------------------|
| PASS     | No issues                              |
| WARN     | Warnings only, no blockers             |
| BLOCKED  | At least one blocker                   |
| FAIL     | Structural invalidity (bad task IDs)   |

FAIL takes precedence over BLOCKED.

## Functions

- `validate_prd_task_queue(tasks, start_task_id, end_task_id)` → `PrdTaskQueueValidationReport`
- `validate_task_range_contiguous(tasks, start_task_id, end_task_id)` → `List[str]`
- `validation_report_to_dict(report)` → `Dict`
- `validation_report_to_markdown(report)` → `str`

## Tests

```bash
python3 -m pytest tests/unit/test_prd_task_queue_validator.py -v
```
