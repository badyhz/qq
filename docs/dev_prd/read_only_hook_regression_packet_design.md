# Read-Only Hook Regression Packet Design

## Purpose

Define the regression packet structure used to detect changes in hook behavior across versions. The packet compares a baseline evidence record against a new one and produces a verdict.

## Contract

```yaml
regression_packet:
  hook_id: string
  baseline_evidence: object
  new_evidence: object
  diff: object
  verdict: enum
```

## Fields / Items

### hook_id
- Type: `string`
- Identifies the hook being regression-tested.

### baseline_evidence
- Type: `object`
- An `evidence_record` from a known-good run.
- Source: stored from a previous verified invocation.
- See `read_only_hook_evidence_model.md` for structure.

### new_evidence
- Type: `object`
- An `evidence_record` from the current run.
- Source: produced by the hook invocation under test.

### diff
- Type: `object`
- Fields:
  - `result_changed`: boolean. True if `baseline_evidence.result != new_evidence.result`.
  - `invariants_diff`: list of invariant IDs that differ between baseline and new.
  - `invariants_added`: list of invariant IDs present in new but not baseline.
  - `invariants_removed`: list of invariant IDs present in baseline but not new.
  - `operation_changed`: boolean. True if operation differs.

### verdict
- Type: `enum`
- Values: `MATCH`, `DRIFT`, `REGRESSION`, `IMPROVEMENT`
- `MATCH`: no differences detected.
- `DRIFT`: invariant set changed but results are equivalent.
- `REGRESSION`: result status degraded (e.g., `OK` -> `INVARIANT_VIOLATION`).
- `IMPROVEMENT`: result status improved (e.g., `INVARIANT_VIOLATION` -> `OK`).

## Rules

1. Deterministic diff. Same two evidence records always produce the same diff.
2. No network comparison. Diff is computed locally from two evidence records.
3. No I/O during diff computation.
4. Baseline evidence MUST be provided by the caller; hook system does not fetch it.
5. Verdict classification is based solely on `result_status` field comparison.
6. Regression packet is immutable once constructed.

## Safety

- Regression packet contains no secrets or live data.
- Regression packet is a pure function of two evidence records.
- Regression packet does not access filesystem, network, or runtime state.
- `REGRESSION` verdict triggers an alert for manual review.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
