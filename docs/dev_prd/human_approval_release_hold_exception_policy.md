# Human Approval Release Hold Exception Policy

**Task ID:** T1299
**release_hold:** HOLD

## Purpose

Defines the sole mechanism by which release_hold may transition from
HOLD to a released state. This is the exception path — the default
is HOLD with no exceptions.

## Default State

- release_hold = HOLD for all evidence packs
- No pack may assume release_hold is not HOLD
- No automated system may change release_hold

## Exception Requirements

release_hold may only change if ALL of the following are true:

1. Human reviewer explicitly documents the exception
2. A separate approval chain (not the pack reviewer) authorizes it
3. The exception is logged in a dedicated exception ledger
4. The exception has an expiry — no permanent exceptions
5. The exception scope is limited to specific frozen files

## Exception Record Format

| Field | Type | Constraint |
|-------|------|------------|
| exception_id | UUID | Unique, non-reusable |
| requested_by | string | Human identity, not service account |
| authorized_by | string | Different human from requested_by |
| scope | list[string] | Specific frozen file paths |
| justification | string | Minimum 50 characters |
| expiry | ISO 8601 | MUST be in the future |
| ledger_entry_id | string | Reference to exception ledger |

## Validation Rules

- `requested_by` and `authorized_by` MUST be different humans
- `scope` MUST list specific files — no wildcard, no "all"
- `justification` MUST be substantive, not boilerplate
- `expiry` MUST be in the future, maximum 72 hours from creation
- `ledger_entry_id` MUST reference an existing ledger entry

## Rejection Conditions

Exception is rejected if:

- requested_by equals authorized_by (self-authorization)
- scope is empty or contains wildcards
- justification is below minimum length
- expiry is in the past or beyond 72-hour limit
- ledger entry does not exist

## Constraints

- No permanent exceptions
- No self-authorized exceptions
- No scope-free exceptions
- No exceptions without ledger entry
- Default remains HOLD even if exception is approved — exception
  only permits the promotion to proceed, not automatic release
