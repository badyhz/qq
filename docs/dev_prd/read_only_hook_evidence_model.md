# Read-Only Hook Evidence Model

## Purpose

Define the evidence record structure produced by every read-only hook invocation. Evidence is the audit trail proving what happened during a hook call.

## Contract

```yaml
evidence_record:
  hook_id: string
  timestamp: string
  operation: string
  result: enum
  invariants_checked: list
  invariants_passed: list
```

## Fields / Items

### hook_id
- Type: `string`
- Source: input `hook_id`.
- Identifies which hook produced this evidence.

### timestamp
- Type: `string`
- Format: ISO 8601 (e.g., `2026-05-27T10:00:00Z`)
- Source: input `context.timestamp`.
- MUST be passed in; hook MUST NOT generate its own timestamp.
- Rationale: prevents time-based side effects and ensures reproducibility.

### operation
- Type: `string`
- Source: input `operation_kind`.
- Records what operation was attempted.

### result
- Type: `enum`
- Source: output `result_status`.
- Values: `OK`, `PERMISSION_DENIED`, `INVARIANT_VIOLATION`, `SANITIZATION_FAILURE`, `TIMEOUT`, `UNKNOWN`.

### invariants_checked
- Type: `list` of `string`
- Lists all invariant IDs that were evaluated during this invocation.
- Order matches the invariant plan declaration order.

### invariants_passed
- Type: `list` of `string`
- Lists invariant IDs that passed.
- Subset of `invariants_checked`.
- If `invariants_passed == invariants_checked`, all invariants passed.

## Rules

1. No auto-generated timestamps. Timestamp comes from `context.timestamp` only.
2. No I/O during evidence construction. Evidence is a pure function of hook execution.
3. Evidence record is always produced, even on failure.
4. Evidence record is immutable once constructed.
5. `invariants_checked` MUST match the declared invariant set for the hook's `operation_kind`.
6. Evidence record is included in the hook's output and in the regression packet.

## Safety

- Evidence record contains no secrets, credentials, or live data.
- Evidence record is deterministic for the same input and hook behavior.
- Evidence record does not reference mutable state.
- Evidence record is serializable to JSON without loss.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
