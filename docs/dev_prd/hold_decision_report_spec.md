# Hold Decision Report Specification (T1473)

## Purpose

Defines the report format justifying continued hold on frozen files.

## Report Structure

```
HoldDecisionReport:
  file_path: str                       # target frozen file
  report_timestamp: str                # ISO 8601 UTC
  hold_reason: str                     # primary reason for hold
  readiness_score: PromotionReadinessScore
  blockers: list[Blocker]             # specific blocking issues
  review_history: list[ReviewSummary]  # prior review attempts
  next_review_date: str               # when to re-review (ISO 8601)
  escalation_status: str              # NONE | PENDING | ESCALATED
  recommendation: str                 # CONTINUE_HOLD | ESCALATE | RE_REVIEW
```

## Blocker Structure

```
Blocker:
  dimension: str          # scoring dimension
  current_score: float    # current value
  required_score: float   # minimum required
  description: str        # what needs to change
  remediation: str        # suggested action
```

## Review Summary Structure

```
ReviewSummary:
  review_date: str        # ISO 8601
  reviewer_id: str        # who reviewed
  decision: str           # APPROVE | REJECT | DEFER | ESCALATE
  score_at_review: float  # readiness score at that time
```

## Decision Logic

```
if any blocker is CRITICAL:
  recommendation = ESCALATE
elif blockers are decreasing over time:
  recommendation = RE_REVIEW (with next_review_date)
else:
  recommendation = CONTINUE_HOLD
```

## Constraints

- Report is a snapshot. Does not trigger actions.
- No automated escalation. Documentation only.
- Release hold: HOLD
