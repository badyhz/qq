# Runtime Governance Blocker Summary

Summarizes blockers from a `RuntimeGovernancePreflightPacket`. Pure. Deterministic. No I/O.

## Data Model

**`RuntimeGovernanceBlockerSummary`** (frozen dataclass):
- `total_blockers` — total number of governance failures
- `critical_blockers` — failures with `CRITICAL` severity
- `policy_blockers` — failures with `POLICY_BLOCK` category
- `by_category` — `Dict[str, int]` mapping failure category to count
- `by_source` — `Dict[str, int]` mapping failure source to count
- `recommended_action` — `"PROCEED"`, `"REVIEW"`, or `"BLOCK"`

## Action Logic

| Condition | Action |
|---|---|
| No blockers | `PROCEED` |
| Non-critical blockers only | `REVIEW` |
| Any critical or policy blockers | `BLOCK` |

## Usage

```python
from core.runtime_governance_preflight_packet import (
    build_runtime_governance_preflight_packet,
)
from core.runtime_governance_blocker_summary import (
    summarize_runtime_governance_blockers,
    blocker_summary_to_dict,
    blocker_summary_to_markdown,
)

# assume `packet` is a RuntimeGovernancePreflightPacket
summary = summarize_runtime_governance_blockers(packet)
print(summary.recommended_action)  # "PROCEED" / "REVIEW" / "BLOCK"

d = blocker_summary_to_dict(summary)
md = blocker_summary_to_markdown(summary)
```

## Dependencies

- `core.runtime_governance_preflight_packet` — `RuntimeGovernancePreflightPacket`
- `core.governance_failure_taxonomy` — `FailureCategory`, `FailureSeverity`, `GovernanceFailure`

## Module

`core.runtime_governance_blocker_summary`
