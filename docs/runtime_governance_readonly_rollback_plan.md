# T845: Runtime Governance Read-Only Rollback Plan

## Purpose

Static rollback plan for future read-only implementation. Pure, deterministic — no I/O, no timestamps, no random.

## Data Model

`RuntimeGovernanceReadOnlyRollbackStep` (frozen dataclass):
- `step_id`: unique identifier
- `trigger`: condition that activates rollback
- `action`: corrective action
- `verification`: how to confirm rollback succeeded
- `owner`: responsible party

## Rollback Steps

| step_id | trigger | action | verification | owner |
|---------|---------|--------|--------------|-------|
| unexpected_write_detected | unexpected write permission | halt implementation | invariant checker shows no write | governance controller |
| network_call_detected | network call detected | halt implementation | invariant checker shows no network | governance controller |
| secret_access_detected | secret access detected | halt implementation | invariant checker shows no secret | governance controller |
| planner_bypass_detected | planner bypass detected | halt implementation | planner integration frozen | governance controller |
| permission_creep_detected | permission creep detected | revert to last clean state | permission envelope clean | governance controller |

## API

```python
from core.runtime_governance_readonly_rollback_plan import (
    build_readonly_rollback_plan,
    readonly_rollback_plan_to_dict,
    readonly_rollback_plan_to_markdown,
)

steps = build_readonly_rollback_plan()
as_dict = readonly_rollback_plan_to_dict(steps)
as_md = readonly_rollback_plan_to_markdown(steps)
```
