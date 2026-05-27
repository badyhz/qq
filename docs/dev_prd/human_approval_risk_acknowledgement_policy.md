# Human Approval Risk Acknowledgement Policy

**Task ID:** T1296
**release_hold:** HOLD

## Purpose

Requires explicit human acknowledgement of risks before approving
any frozen file promotion. No implicit or default acceptance allowed.

## Acknowledgement Requirements

Reviewer MUST explicitly acknowledge:

1. **Frozen file risk** — modifying frozen files may break production
2. **Downstream impact** — changes may affect dependent modules
3. **Rollback cost** — reverting may require manual intervention
4. **Testing gap** — dry-run may not cover all edge cases

## Acknowledgement Format

The risk acknowledgement field MUST contain:

| Field | Type | Constraint |
|-------|------|------------|
| acknowledged | boolean | MUST be `true` |
| reviewer_signature | string | MUST match reviewer_id |
| acknowledgement_timestamp | ISO 8601 | MUST be between review_started and review_completed |
| risk_summary | string | MUST describe understood risks in reviewer's words |

## Validation Rules

- `acknowledged` MUST be explicitly `true` — no default, no null
- `reviewer_signature` MUST match pack's reviewer_id
- `risk_summary` MUST be non-empty, minimum 20 characters
- `risk_summary` MUST NOT be auto-generated template text

## Rejection Conditions

Pack is rejected if:

- `acknowledged` is false, null, or missing
- `reviewer_signature` does not match reviewer_id
- `risk_summary` is empty or below minimum length
- `risk_summary` matches a known auto-fill pattern
- Timestamp is outside review window

## Constraints

- No risk acknowledgement on behalf of another person
- No batch risk acknowledgement across multiple packs
- No risk acknowledgement without reading the evidence pack
- No risk acknowledgement that omits frozen file list
- release_hold = HOLD — acknowledgement does not grant release
