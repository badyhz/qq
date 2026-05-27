# Human Approval Rollback Acknowledgement Policy

**Task ID:** T1297
**release_hold:** HOLD

## Purpose

Requires explicit human acknowledgement of rollback procedures before
approving any frozen file promotion. Reviewer must understand how to
undo the promotion if issues arise.

## Acknowledgement Requirements

Reviewer MUST explicitly acknowledge:

1. **Rollback exists** — a documented rollback procedure is available
2. **Rollback tested** — rollback procedure has been validated in dry-run
3. **Rollback cost** — reviewer understands effort to execute rollback
4. **Rollback scope** — reviewer knows which files and modules are affected

## Acknowledgement Format

| Field | Type | Constraint |
|-------|------|------------|
| acknowledged | boolean | MUST be `true` |
| reviewer_signature | string | MUST match reviewer_id |
| rollback_plan_ref | string | MUST reference existing rollback document |
| rollback_tested | boolean | MUST be `true` |
| acknowledgement_timestamp | ISO 8601 | MUST be between review_started and review_completed |

## Validation Rules

- `acknowledged` MUST be explicitly `true`
- `reviewer_signature` MUST match pack's reviewer_id
- `rollback_plan_ref` MUST reference a document that exists
- `rollback_tested` MUST be `true` — untested rollback = reject
- Timestamp ordering MUST be valid

## Rollback Document Requirements

The referenced rollback document MUST contain:

- Exact git commands to revert promotion
- List of files affected by rollback
- Order of operations (sequence matters)
- Expected state after rollback

## Rejection Conditions

Pack is rejected if:

- `acknowledged` is false, null, or missing
- `rollback_plan_ref` points to nonexistent document
- `rollback_tested` is false
- Rollback document is incomplete

## Constraints

- No acknowledgement without reading rollback document
- No acknowledgement without verifying rollback was tested
- No auto-populated rollback acknowledgement
- release_hold = HOLD — acknowledgement does not grant release
