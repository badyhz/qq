# Read-Only Hook Output Contract

## Purpose

Define the output structure for all read-only hook invocations. Every call out of a read-only hook MUST produce exactly these fields, no more, no less.

## Contract

```yaml
output:
  result_status: enum
  sanitized_output: object
  evidence_record: object
  invariant_results: list
  side_effects_declared: list
```

## Fields / Items

### result_status
- Type: `enum`
- Allowed values: `OK`, `PERMISSION_DENIED`, `INVARIANT_VIOLATION`, `SANITIZATION_FAILURE`, `TIMEOUT`, `UNKNOWN`
- Required: YES
- Single field summarizing the outcome.

### sanitized_output
- Type: `object`
- Required: YES
- Contains the hook's analysis result with all sensitive fields redacted.
- Structure is defined per hook type.
- MUST NOT contain live market data, live account balances, or credentials.

### evidence_record
- Type: `object`
- Required: YES
- See `read_only_hook_evidence_model.md` for full schema.
- Contains: `hook_id`, `timestamp`, `operation`, `result`, `invariants_checked`, `invariants_passed`.

### invariant_results
- Type: `list`
- Required: YES
- Each item: `{ invariant_id: string, passed: boolean, detail: string }`
- Every declared invariant MUST appear exactly once.

### side_effects_declared
- Type: `list`
- Required: YES
- Expected to be empty `[]` for all read-only hooks.
- Exists for audit: if a future modification introduces a side effect, it MUST be declared here.

## Rules

1. No live data in output. All values are snapshots, copies, or derived computations.
2. Deterministic: same input always produces same output (modulo declared randomness seeds).
3. `side_effects_declared` MUST be empty for read-only hooks. Non-empty = `INVARIANT_VIOLATION`.
4. `evidence_record` is always present, even on failure.
5. `invariant_results` length MUST match the declared invariant set for the hook's `operation_kind`.

## Safety

- Output construction is a pure function.
- No I/O during output construction.
- No timestamps generated; all timestamps come from input `context.timestamp`.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
