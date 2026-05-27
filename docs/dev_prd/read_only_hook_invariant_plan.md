# Read-Only Hook Invariant Plan

## Purpose

Define the invariants that every read-only hook MUST satisfy. Invariants are the contract's safety guarantees. All invariants MUST be checkable without I/O.

## Contract

```yaml
invariants:
  scope: per-hook
  check_method: pure_function
  required: all
```

## Fields / Items

### Invariant Definitions

| ID | Name | Description | Check Method |
|---|---|---|---|
| INV_NO_MUTATION | No Mutation | Hook does not mutate any input, output, or shared state | Static analysis + test assertion |
| INV_NO_NETWORK | No Network | Hook does not make network calls | Static analysis + test assertion |
| INV_NO_SECRETS | No Secrets | Hook does not access, read, or reference secrets | Static analysis + pattern scan |
| INV_NO_LIVE_PATHS | No Live Paths | Hook does not import or reference live trading modules | Import graph analysis |
| INV_NO_PLANNER_CALLS | No Planner Calls | Hook does not invoke planner, scheduler, or orchestrator | Static analysis + test assertion |
| INV_NO_SUBPROCESS | No Subprocess | Hook does not spawn or communicate with subprocesses | Static analysis + test assertion |
| INV_NO_FILE_WRITE | No File Write | Hook does not write to filesystem | Static analysis + test assertion |
| INV_NO_AUTO_TIMESTAMP | No Auto Timestamp | Hook does not generate timestamps; uses context.timestamp only | Source scan |
| INV_DETERMINISTIC | Deterministic | Same input always produces same output | Property-based test |
| INV_SIDE_EFFECT_FREE | Side Effect Free | `side_effects_declared` is empty | Output assertion |

## Rules

1. All invariants MUST be checkable without I/O. No network, no filesystem, no subprocess for checking.
2. All invariants MUST pass for the hook to return `OK`.
3. Any single invariant failure = `INVARIANT_VIOLATION` result_status.
4. Invariant results are recorded in the evidence record.
5. New invariants require a design doc update and acceptance criteria update.
6. Invariant checks are idempotent: running them twice yields the same result.

## Safety

- Invariant checkers are pure functions.
- Invariant checkers do not depend on runtime state.
- Invariant checkers are themselves tested for correctness.
- Frozen boundary: if the hook's source file is in a FROZEN zone, invariants are additionally verified at freeze time.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
