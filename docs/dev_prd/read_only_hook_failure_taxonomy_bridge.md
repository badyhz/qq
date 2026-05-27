# Read-Only Hook Failure Taxonomy Bridge

## Purpose

Define the complete failure taxonomy for read-only hooks. Every failure mode MUST map to a defined category. No silent failures are permitted.

## Contract

```yaml
failure_taxonomy:
  categories: list
  reporting: mandatory
  silent_failures: prohibited
```

## Fields / Items

### Failure Categories

| Category | Code | Description | Trigger |
|---|---|---|---|
| PERMISSION_DENIED | `PERM_001` | Caller lacks required read-only flags | Permission adapter returns empty flags or caller flags not in required set |
| INVARIANT_VIOLATION | `INV_001` | One or more invariants failed | Any invariant in `invariant_results` has `passed: false` |
| SANITIZATION_FAILURE | `SAN_001` | Sanitizer could not process payload | Unrecognizable structure, redaction logic error, or pattern match failure |
| TIMEOUT | `TIME_001` | Hook execution exceeded time limit | Wall-clock timeout exceeded (timeout value from config, not hook) |
| UNKNOWN | `UNK_001` | Unrecognized failure mode | Any exception not caught by above categories |

### Failure Report Structure

```yaml
failure_report:
  category: enum
  code: string
  detail: string
  hook_id: string
  timestamp: string (from context)
  evidence_record: object (always present, even on failure)
```

### Failure Handling Flow

1. Hook invocation begins.
2. If permission check fails: `PERMISSION_DENIED`. Evidence recorded. Return.
3. If sanitization fails: `SANITIZATION_FAILURE`. Evidence recorded. Return.
4. Hook logic executes.
5. If invariant fails: `INVARIANT_VIOLATION`. Evidence recorded. Return.
6. If timeout: `TIMEOUT`. Evidence recorded. Return.
7. If any other error: `UNKNOWN`. Evidence recorded. Return.
8. On success: `OK`. Evidence recorded. Return.

## Rules

1. All failures MUST be caught and reported. No exceptions escape the hook boundary.
2. No silent failures. Every failure produces a `failure_report` with non-empty `detail`.
3. `UNKNOWN` category is a safety net; every effort SHOULD map to a specific category first.
4. Failure reports include the evidence record for audit.
5. Failure categories are extensible only via design doc update.
6. Error handling itself MUST NOT have side effects.

## Safety

- Failure handling does not write to filesystem, network, or subprocess.
- Failure handling does not access secrets.
- Failure handling is deterministic for the same input.
- The `UNKNOWN` category triggers an alert for manual review.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
