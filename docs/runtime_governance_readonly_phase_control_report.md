# T838 — Runtime Governance Read-Only Phase Control Report

## Purpose

Gate control: determine if read-only design may move to manual review.

## Decision Logic

| Condition | Decision |
|-----------|----------|
| blocker_action == "BLOCK" | HOLD |
| readiness_grade not in (A, B) | REVIEW |
| otherwise | PROCEED_TO_MANUAL_REVIEW_ONLY |

Priority: BLOCK check first, then grade check, then default proceed.

## Dependencies

- `core.runtime_governance_readonly_regression_packet` — regression verdict
- `core.runtime_governance_readonly_readiness_score` — readiness grade
- `core.runtime_governance_readonly_blocker_summary` — blocker action

## API

```python
from core.runtime_governance_readonly_phase_control_report import (
    build_readonly_phase_control_report,
    readonly_phase_control_report_to_dict,
    readonly_phase_control_report_to_markdown,
)

report = build_readonly_phase_control_report()  # default: PROCEED_TO_MANUAL_REVIEW_ONLY
d = readonly_phase_control_report_to_dict(report)
md = readonly_phase_control_report_to_markdown(report)
```

## Constraints

- Pure, deterministic
- No I/O, no timestamps, no random
- Frozen dataclass
