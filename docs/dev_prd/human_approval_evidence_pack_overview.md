# Human Approval Evidence Pack Overview

**Task ID:** T1291
**release_hold:** HOLD

## Purpose

Defines the master structure for human approval evidence packs.
Every frozen file promotion requires a complete evidence pack
before a human reviewer may grant approval.

## Scope

- Applies to all frozen file promotions across all risk tiers
- Covers evidence pack composition, validation, and archival
- Does not grant any execution or submission authority
- release_hold remains HOLD throughout all phases

## Evidence Pack Components

An evidence pack MUST contain:

1. **Reviewer Identity** (T1293) — who approved
2. **Timestamp Record** (T1294) — when approval occurred
3. **Command Transcript** (T1295) — what commands were reviewed
4. **Risk Acknowledgement** (T1296) — explicit risk sign-off
5. **Rollback Acknowledgement** (T1297) — rollback plan sign-off
6. **Dry-Run Evidence** (T1298) — dry-run validation proof
7. **Release Hold Exception** (T1299) — if any hold was lifted, justification

## Validation Rules

- Pack is incomplete if any required field is missing
- Incomplete packs MUST be rejected — no partial approvals
- Missing fields trigger return to reviewer, not auto-fill
- All fields are immutable once pack is sealed

## Lifecycle

```
DRAFT → SUBMITTED → REVIEWED → APPROVED | REJECTED → ARCHIVED
```

- DRAFT: reviewer populates fields
- SUBMITTED: pack locked for review
- REVIEWED: human reads pack, makes decision
- APPROVED/REJECTED: terminal state
- ARCHIVED: stored for audit trail

## Constraints

- No automated approval — human must read and sign
- No approval without complete pack
- No promotion without approved pack
- release_hold = HOLD unless T1299 exception applies
