# T848: Runtime Governance Read-Only Future Task Queue

Generate future tasks as data only. Pure, deterministic, no I/O, no timestamps, no random.

## Data Model

`RuntimeGovernanceReadOnlyFutureTask` (frozen dataclass):
- `task_id: str`
- `title: str`
- `risk_level: str` — "low", "medium", "high", "critical"
- `status: str` — "queued", "blocked", "ready"
- `dependencies: List[str]`
- `notes: List[str]`

## Functions

| Function | Returns |
|----------|---------|
| `build_readonly_future_task_queue()` | `List[RuntimeGovernanceReadOnlyFutureTask]` |
| `readonly_future_task_queue_to_dict(tasks)` | `List[Dict]` |
| `readonly_future_task_queue_to_markdown(tasks)` | `str` |

## Future Tasks

| task_id | title | risk | status | dependencies |
|---------|-------|------|--------|--------------|
| FUTURE-RO-001 | implement read-only hook prototype | high | blocked | manual approval, readiness score >= B |
| FUTURE-RO-002 | add pure adapter facade | medium | blocked | read-only hook prototype |
| FUTURE-RO-003 | add manual review CLI | low | queued | pure adapter facade |
| FUTURE-RO-004 | add observability hooks | medium | queued | read-only hook prototype |
| FUTURE-RO-005 | add threat model validation | high | queued | observability hooks |

No tasks are `ready` — no live auth available yet.
