# T846: Runtime Governance Read-Only Observability Design

## Purpose

Static design for a future read-only observation layer in the runtime governance system. No I/O, no timestamps, no logging implementation.

## Observation Points

| point_id | signal | sensitivity | allowed_storage | redaction |
|---|---|---|---|---|
| permission_check | permission envelope evaluation | low | local log | none |
| invariant_result | invariant checker result | low | local log | none |
| scenario_verdict | scenario evaluation verdict | low | local log | none |
| blocker_summary | blocker summary | medium | local log | none |
| readiness_score | readiness score | medium | local log | none |
| phase_decision | phase control decision | high | encrypted | none |
| approval_status | approval form status | critical | encrypted | full |

## Sensitivity Rules

- **low**: local log, no redaction
- **medium**: local log, no redaction
- **high**: encrypted storage, no redaction
- **critical**: encrypted storage, full redaction

## API

```python
from core.runtime_governance_readonly_observability_design import (
    build_readonly_observability_design,
    readonly_observability_design_to_dict,
    readonly_observability_design_to_markdown,
)

points = build_readonly_observability_design()  # List[RuntimeGovernanceReadOnlyObservationPoint]
as_dicts = readonly_observability_design_to_dict(points)
as_md = readonly_observability_design_to_markdown(points)
```

## Constraints

- Pure functions, deterministic
- No I/O, no timestamps, no random
- Frozen dataclass (immutable)
- No raw secrets in any field
