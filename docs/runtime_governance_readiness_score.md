# Runtime Governance Readiness Score

Pure scoring model for runtime governance regression packets.

## Overview

`RuntimeGovernanceReadinessScore` converts a `RuntimeGovernanceRegressionPacket` into a numeric score with letter grade.

## Data Model

```python
@dataclass(frozen=True)
class RuntimeGovernanceReadinessScore:
    score: int          # 0-100
    max_score: int      # always 100
    percent: float      # score/max_score * 100
    grade: str          # A / B / C / D / F
    blockers: List[str] # critical issues
    warnings: List[str] # non-critical issues
    notes: List[str]    # metadata
```

## Scoring Rules

| Source | Penalty |
|---|---|
| Start | 100 |
| Each scenario fail | -10 |
| Each invariant error | -5 |
| Manifest WARN | -5 |
| Manifest FAIL | -20 |

Score is clamped to [0, 100].

## Grade Thresholds

| Grade | Min Score |
|---|---|
| A | 90 |
| B | 75 |
| C | 60 |
| D | 40 |
| F | < 40 |

**BLOCKED blocker:** Any BLOCKED blocker caps grade at F regardless of score.

## API

```python
from core.runtime_governance_readiness_score import (
    compute_runtime_governance_readiness_score,
    readiness_score_to_dict,
    readiness_score_to_markdown,
)

packet = build_runtime_governance_regression_packet()
score = compute_runtime_governance_readiness_score(packet)
print(score.grade)  # A

d = readiness_score_to_dict(score)
md = readiness_score_to_markdown(score)
```

## Dependencies

- `core.runtime_governance_regression_packet.RuntimeGovernanceRegressionPacket`

## Properties

- Pure: no I/O, no network, no random, no timestamps
- Deterministic: same packet always produces same score
- Frozen dataclass: immutable results
