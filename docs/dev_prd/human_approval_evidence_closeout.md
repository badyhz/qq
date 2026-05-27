# Human Approval Evidence Closeout

**Task ID:** T1300
**release_hold:** HOLD

## Purpose

Defines the closeout procedure for human approval evidence packs.
Ensures all packs are properly archived and audit trails are complete.

## Closeout Prerequisites

Pack may be closed only when:

1. All required fields are validated (T1292)
2. Reviewer identity is confirmed (T1293)
3. All timestamps are valid and ordered (T1294)
4. Command transcript is complete (T1295)
5. Risk acknowledgement is signed (T1296)
6. Rollback acknowledgement is signed (T1297)
7. Dry-run evidence passes (T1298)
8. Release hold exception (if any) is valid (T1299)

## Closeout States

| State | Description |
|-------|-------------|
| APPROVED | All checks passed, promotion may proceed |
| REJECTED | One or more checks failed, promotion blocked |
| EXPIRED | Pack exceeded maximum review window without decision |
| WITHDRAWN | Reviewer or author cancelled the pack |

## Archive Requirements

Closed packs MUST be archived with:

- All original fields preserved (immutable copy)
- Closeout timestamp (auto-generated)
- Closeout state (APPROVED / REJECTED / EXPIRED / WITHDRAWN)
- Closeout reason (free-text from reviewer)

## Retention

- Approved packs: retained indefinitely
- Rejected packs: retained for audit trail, minimum 1 year
- Expired packs: retained for 90 days
- Withdrawn packs: retained for 90 days

## Post-Closeout

After closeout:

- Pack is read-only — no modifications permitted
- Archival location is immutable
- Pack may be retrieved for audit at any time
- Pack references (pack_id) remain valid permanently

## Constraints

- No closeout without all prerequisites met
- No modification after closeout
- No deletion of closed packs
- No closeout bypass for any risk tier
- release_hold = HOLD — closeout does not grant release
