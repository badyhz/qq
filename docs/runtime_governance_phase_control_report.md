# Runtime Governance Phase Control Report

Summarizes whether the project may advance beyond the pre-live audit layer.

## Module

`core/runtime_governance_phase_control_report.py`

## Dataclass

```python
@dataclass(frozen=True)
class RuntimeGovernancePhaseControlReport:
    phase: str                    # always "pre-live audit"
    regression_verdict: str       # PASS / FAIL / BLOCKED
    readiness_grade: str          # A / B / C / D / F
    blocker_action: str           # BLOCK / PROCEED
    no_submit_verdict: str        # PASS / FAIL
    final_decision: str           # HOLD / REVIEW / PROCEED_TO_MANUAL_SCOPE_ONLY
    notes: List[str]
```

## Functions

| Function | Returns | Pure |
|---|---|---|
| `build_runtime_governance_phase_control_report(*)` | `RuntimeGovernancePhaseControlReport` | Yes |
| `phase_control_report_to_dict(report)` | `Dict` | Yes |
| `phase_control_report_to_markdown(report)` | `str` | Yes |

## Decision Logic

Priority-ordered:

1. **HOLD** — if any blocker action is `BLOCK`
2. **HOLD** — if no-submit evidence verdict is not `PASS`
3. **REVIEW** — if readiness grade is below B (C, D, or F)
4. **PROCEED_TO_MANUAL_SCOPE_ONLY** — if all checks pass

The system **never** declares readiness for live trading.

## Dependencies

| Module | Function |
|---|---|
| `core.runtime_governance_regression_packet` | `build_runtime_governance_regression_packet` |
| `core.runtime_governance_readiness_score` | `compute_runtime_governance_readiness_score` |
| `core.runtime_governance_blocker_summary` | `summarize_runtime_governance_blockers` |
| `core.runtime_governance_no_submit_evidence_packet` | `build_runtime_governance_no_submit_evidence_packet` |
| `core.runtime_governance_preflight_packet` | `build_runtime_governance_preflight_packet` |

## Example

```python
from core.runtime_governance_phase_control_report import (
    build_runtime_governance_phase_control_report,
    phase_control_report_to_markdown,
)

report = build_runtime_governance_phase_control_report()
print(report.final_decision)
# PROCEED_TO_MANUAL_SCOPE_ONLY (or REVIEW depending on readiness)

print(phase_control_report_to_markdown(report))
```
