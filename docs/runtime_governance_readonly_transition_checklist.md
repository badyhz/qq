# T840 — Runtime Governance Read-Only Transition Checklist

## Purpose

Checklist for human review before any future read-only hook implementation.

## Design

- Pure dataclass, frozen=True
- Deterministic: no I/O, no timestamps, no random
- 8 items, all required, all complete

## Checklist Items

| # | Item ID | Description |
|---|---------|-------------|
| 1 | permission_envelope_reviewed | Permission envelope reviewed and validated |
| 2 | invariant_checker_reviewed | Invariant checker reviewed and validated |
| 3 | no_dangerous_side_effects | No dangerous side effects declared |
| 4 | scenario_catalog_reviewed | Read-only scenario catalog reviewed |
| 5 | regression_packet_passes | Regression packet all PASS |
| 6 | readiness_score_acceptable | Readiness score >= B grade |
| 7 | blocker_summary_clean | Blocker summary shows PROCEED |
| 8 | phase_control_approved | Phase control allows PROCEED_TO_MANUAL_REVIEW_ONLY |

## API

```python
from core.runtime_governance_readonly_transition_checklist import (
    build_readonly_transition_checklist,
    readonly_transition_checklist_to_dict,
    readonly_transition_checklist_to_markdown,
    summarize_readonly_transition_checklist,
)

items = build_readonly_transition_checklist()
summary = summarize_readonly_transition_checklist(items)
# {"total": 8, "required": 8, "complete": 8, "pending": 0}
```

## Files

- `core/runtime_governance_readonly_transition_checklist.py` — implementation
- `tests/unit/test_runtime_governance_readonly_transition_checklist.py` — tests
- `docs/runtime_governance_readonly_transition_checklist.md` — this file
