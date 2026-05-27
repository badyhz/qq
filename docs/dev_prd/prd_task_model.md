# PRD Task Model — T865

Pure dataclasses for PRD task queue items.

## Dataclasses

### PrdTask (frozen=True)

| Field                | Type         | Description                        |
|----------------------|--------------|------------------------------------|
| task_id              | str          | T<digits>, e.g. T865              |
| title                | str          | Human-readable task title          |
| status               | str          | See valid statuses below           |
| allowed_files        | List[str]    | Files this task may modify         |
| dependencies         | List[str]    | task_ids that must complete first  |
| acceptance_commands  | List[str]    | CLI commands to verify completion  |
| risk_level           | str          | See valid risk levels below        |
| notes                | List[str]    | Free-form notes                    |

### PrdTaskRange (frozen=True)

| Field           | Type         | Description                           |
|-----------------|--------------|---------------------------------------|
| start_task_id   | str          | First task in range                   |
| end_task_id     | str          | Last task in range                    |
| tasks           | List[PrdTask]| Ordered list of tasks                 |
| hard_stop_task_id| str         | Do not execute beyond this task_id    |
| notes           | List[str]    | Range-level notes                     |

## Valid Values

**Status:** COMPLETED, NOT_STARTED, HUMAN_REVIEW_REQUIRED, IN_PROGRESS, BLOCKED, PARTIAL

**Risk:** LOW, MEDIUM, HIGH, FROZEN

## Functions

| Function              | Returns           | Description                              |
|-----------------------|-------------------|------------------------------------------|
| validate_task_id      | bool              | True if T<digits>                        |
| parse_task_number     | int               | Numeric part, raises ValueError          |
| task_to_dict          | Dict[str, Any]    | Stable serialization                     |
| task_range_to_dict    | Dict[str, Any]    | Nested serialization                     |
| task_to_markdown      | str               | Deterministic markdown                   |
| task_range_to_markdown| str               | Full range markdown                      |
| summarize_task_range  | Dict[str, Any]    | Status/risk counts, range metadata       |

## Rules

- Pure deterministic only, no I/O, no timestamps, no random.
- Frozen dataclasses: mutation after construction is not allowed.
- List fields are copied in serializers to prevent mutation leaking.
