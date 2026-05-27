# Human Approval Required Fields

**Task ID:** T1292
**release_hold:** HOLD

## Purpose

Specifies all mandatory fields in a human approval evidence pack.
No field is optional. Missing any field invalidates the pack.

## Required Fields

| Field | Type | Policy |
|-------|------|--------|
| reviewer_id | string | T1293 |
| approval_timestamp | ISO 8601 | T1294 |
| command_transcript | list[string] | T1295 |
| risk_acknowledgement | boolean + signature | T1296 |
| rollback_acknowledgement | boolean + signature | T1297 |
| dry_run_evidence | object | T1298 |
| release_hold_exception | object or null | T1299 |
| pack_id | UUID | auto-generated |
| target_frozen_files | list[string] | from promotion request |

## Field Constraints

- `reviewer_id` — MUST resolve to active human identity, not service account
- `approval_timestamp` — MUST be after all evidence collection timestamps
- `command_transcript` — MUST include every command executed against target files
- `risk_acknowledgement` — MUST be explicitly `true`, no default
- `rollback_acknowledgement` — MUST be explicitly `true`, no default
- `dry_run_evidence` — MUST contain pass/fail status and log reference
- `release_hold_exception` — MUST be null unless T1299 exception is documented
- `pack_id` — UUID v4, unique, non-reusable
- `target_frozen_files` — MUST match promotion request file list exactly

## Validation Order

1. Check all fields present
2. Check reviewer_id is valid human
3. Check timestamp ordering
4. Check risk_acknowledgement = true
5. Check rollback_acknowledgement = true
6. Check dry_run_evidence passes
7. Check release_hold_exception consistency
8. If all pass → pack valid; else → reject

## Constraints

- No field may be auto-populated except pack_id
- No field may be backdated
- No field may reference external state that changes after seal
- release_hold = HOLD — this field does not grant release
