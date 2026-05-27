# Human Approval Transcript Specification (T1471)

## Purpose

Defines the record format for human decisions on frozen file promotion.

## Transcript Structure

```
HumanApprovalTranscript:
  file_path: str                  # target frozen file
  decision: str                   # APPROVE | REJECT | DEFER | ESCALATE
  decision_timestamp: str         # ISO 8601 UTC
  reviewer_id: str                # human reviewer identifier
  reviewer_role: str              # e.g. "governance_lead", "security_reviewer"
  readiness_score: float          # promotion readiness score at time of decision
  risk_acknowledgement: bool      # reviewer acknowledges risk
  rollback_acknowledgement: bool  # reviewer acknowledges rollback plan
  conditions: list[str]           # conditions attached to approval (if any)
  notes: str                      # free-form reviewer notes
  evidence_refs: list[str]        # references to supporting evidence
```

## Validation Rules

- `decision` must be one of: APPROVE, REJECT, DEFER, ESCALATE
- `decision_timestamp` must be ISO 8601 UTC
- `reviewer_id` must be non-empty
- `risk_acknowledgement` must be True for APPROVE decisions
- `rollback_acknowledgement` must be True for APPROVE decisions
- `conditions` required for DEFER decisions

## Decision State Machine

```
DEFER -> reviewer adds conditions -> conditions met -> APPROVE or REJECT
ESCALATE -> higher authority reviews -> APPROVE or REJECT
APPROVE -> file eligible for unlock
REJECT -> file remains frozen, new review cycle required
```

## Constraints

- Transcript is immutable once recorded.
- No automated decisions. Human-only.
- Release hold: HOLD
