# PRD Backlog Schema (T873)

## Overview

Pure schema objects for a 500+ task backlog. No I/O, no timestamps, no random.

## Dataclasses

### PrdBacklogItem (frozen=True)

| Field | Type | Description |
|---|---|---|
| task_id | str | Unique task identifier |
| title | str | Task title |
| milestone_id | str | Milestone this task belongs to |
| wave_id | str | Execution wave |
| batch_id | str | Execution batch |
| risk_level | str | LOW / MEDIUM / HIGH / FROZEN |
| status | str | See valid statuses below |
| dependencies | List[str] | Task IDs this depends on |
| allowed_file_patterns | List[str] | Glob patterns for allowed files |
| forbidden_file_patterns | List[str] | Glob patterns for forbidden files |
| acceptance_command_ids | List[str] | Command IDs for acceptance tests |
| notes | List[str] | Freeform notes |

### PrdBacklog (frozen=True)

| Field | Type | Description |
|---|---|---|
| backlog_id | str | Unique backlog identifier |
| items | List[PrdBacklogItem] | All backlog items |
| total_expected_tasks | int | Expected total (can be 500+) |
| status | str | Backlog-level status |
| notes | List[str] | Freeform notes |

## Constants

**Valid risk levels:** LOW, MEDIUM, HIGH, FROZEN
**Valid statuses:** COMPLETED, NOT_STARTED, HUMAN_REVIEW_REQUIRED, IN_PROGRESS, BLOCKED, PARTIAL

Imported from `core.prd_task_model`.

## Functions

| Function | Signature | Description |
|---|---|---|
| build_backlog_item | (...) -> PrdBacklogItem | Factory with validation |
| backlog_item_to_dict | (item) -> Dict | Serialize item |
| backlog_to_dict | (backlog) -> Dict | Serialize backlog |
| backlog_item_to_markdown | (item) -> str | Markdown for single item |
| backlog_to_markdown | (backlog) -> str | Markdown for full backlog |
| summarize_backlog | (backlog) -> Dict | Counts by risk/status/milestone/wave |
| validate_backlog_item_basic | (item) -> List[str] | Returns issues list, empty if valid |

## Safety

No generated backlog authorizes live trading. This is a schema-only module.

## Usage

```python
from core.prd_backlog_schema import build_backlog_item, PrdBacklog

item = build_backlog_item(
    task_id="T873",
    title="Create backlog schema",
    milestone_id="M4",
    wave_id="W2",
    batch_id="B1",
    risk_level="LOW",
    status="NOT_STARTED",
    dependencies=[],
    allowed_file_patterns=["core/prd_backlog_schema.py"],
    forbidden_file_patterns=[],
    acceptance_command_ids=[],
    notes=[],
)

backlog = PrdBacklog(
    backlog_id="BL-001",
    items=[item],
    total_expected_tasks=500,
    status="NOT_STARTED",
    notes=[],
)
```
