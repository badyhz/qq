# T1191 - Implementation Readiness Scoring Overview

## Purpose

Standardized gate system to evaluate whether a task or wave is ready to proceed. Prevents premature advancement. Forces explicit evidence before human approval.

## Score Dimensions

Six weighted dimensions produce a 0-100% readiness score:

1. TEST_COVERAGE
2. DOCUMENTATION
3. SAFETY_BOUNDARY
4. HUMAN_APPROVAL
5. DEPENDENCY_RESOLUTION
6. REGRESSION_RISK

Each dimension has a threshold. If any dimension falls below threshold, overall verdict is HOLD or BLOCKED regardless of aggregate score.

## Blocker Types

Five blocker categories halt progress:

- MISSING_TESTS
- MISSING_DOCS
- SAFETY_VIOLATION
- UNRESOLVED_DEP
- HIGH_RISK_UNMITIGATED

Each blocker has severity (CRITICAL, HIGH, MEDIUM) and a resolution path.

## Hold States

Four hold states govern flow:

| State | Meaning |
|---|---|
| HOLD_CLEAR | No blockers, proceed |
| HOLD_PENDING_REVIEW | Awaiting human review |
| HOLD_BLOCKED | Active blockers present |
| HOLD_FROZEN | Explicitly frozen by authority |

## Safety Statement

No task advances without passing readiness scoring. No human approval without evidence. No wave transition without all prior wave blockers resolved. No exceptions without explicit override authority.
