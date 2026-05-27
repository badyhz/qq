# PRD 500 Backlog Validator — T904

## Purpose

Deterministic validator for PRD backlogs targeting 500+ tasks.

## Module

`core/prd_500_backlog_validator.py`

## Validation Rules

| Condition | Verdict |
|---|---|
| items >= 500, no duplicates, no unsafe frozen, no live auth, forbidden patterns present | PASS |
| High risk tasks exist but human review present | WARN |
| Frozen tasks have executable status (NOT_STARTED/COMPLETED/IN_PROGRESS) | BLOCKED |
| items < 500 or duplicate task_ids | FAIL |

## Severity Levels

- **fail**: structural violation (count, duplicates)
- **blocker**: safety violation (frozen executable, unsafe frozen patterns, live auth)
- **warning**: advisory (missing forbidden patterns, high risk without review)

## API

```python
from core.prd_500_backlog_validator import (
    validate_prd_500_backlog,
    validation_report_to_dict,
    validation_report_to_markdown,
)

report = validate_prd_500_backlog(backlog)
assert report.final_verdict == "PASS"
```

## Constraints

- Pure deterministic
- No I/O
- No timestamps
- No random
