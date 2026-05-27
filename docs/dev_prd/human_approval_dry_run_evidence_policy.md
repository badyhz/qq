# Human Approval Dry-Run Evidence Policy

**Task ID:** T1298
**release_hold:** HOLD

## Purpose

Requires dry-run validation evidence before any frozen file promotion
can be approved. No promotion proceeds without dry-run proof.

## Evidence Requirements

The dry_run_evidence field MUST contain:

| Field | Type | Constraint |
|-------|------|------------|
| status | enum | `pass` or `fail` — MUST be `pass` |
| run_id | UUID | Unique identifier for the dry-run execution |
| log_reference | string | Path or hash of dry-run log output |
| test_count | integer | Number of tests executed |
| pass_count | integer | Number of tests passed |
| fail_count | integer | Number of tests failed — MUST be 0 |
| run_timestamp | ISO 8601 | When dry-run was executed |

## Validation Rules

- `status` MUST be `pass` — any `fail` rejects the pack
- `fail_count` MUST be 0 — partial passes are not acceptable
- `pass_count` MUST equal `test_count`
- `log_reference` MUST point to an accessible log artifact
- `run_timestamp` MUST be after most recent evidence collection
- `run_id` MUST be unique — no reuse across packs

## Dry-Run Scope

Dry-run MUST cover:

- All target frozen files in the promotion request
- All modules that import or depend on target files
- All configuration paths that reference target files
- Rollback procedure validation

## Rejection Conditions

Pack is rejected if:

- `status` is `fail` or missing
- `fail_count` > 0
- `log_reference` is inaccessible
- Dry-run did not cover all target files
- Dry-run executed before evidence collection started

## Constraints

- No promotion without dry-run evidence
- No cached dry-run results — must be fresh
- No partial dry-run acceptance
- No dry-run bypass for any risk tier
- release_hold = HOLD — dry-run evidence does not grant release
