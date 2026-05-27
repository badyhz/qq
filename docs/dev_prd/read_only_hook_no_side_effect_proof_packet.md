# Read-Only Hook No-Side-Effect Proof Packet

## Purpose

Define the proof structure that demonstrates a read-only hook has zero side effects. The proof combines static analysis results with runtime test assertions.

## Contract

```yaml
proof_packet:
  hook_id: string
  static_analysis: object
  runtime_assertions: object
  verdict: enum
```

## Fields / Items

### hook_id
- Identifies the hook this proof applies to.

### static_analysis
- Type: `object`
- Fields:
  - `file_write_calls`: list of file write operations found in source. Expected: `[]`.
  - `network_calls`: list of network I/O operations found in source. Expected: `[]`.
  - `state_mutations`: list of mutable state references found in source. Expected: `[]`.
  - `subprocess_calls`: list of subprocess invocations found in source. Expected: `[]`.
  - `import_graph`: list of imported modules. Expected: only pure utility modules, no live trading modules.
  - `planner_references`: list of planner/scheduler references found in source. Expected: `[]`.

### runtime_assertions
- Type: `object`
- Fields:
  - `assert_no_file_write`: boolean. True if test confirms no file write.
  - `assert_no_network`: boolean. True if test confirms no network call.
  - `assert_no_state_mutation`: boolean. True if test confirms no state mutation.
  - `assert_no_subprocess`: boolean. True if test confirms no subprocess.
  - `assert_deterministic`: boolean. True if test confirms deterministic output.
  - `assert_side_effects_empty`: boolean. True if `side_effects_declared` is empty.

### verdict
- Type: `enum`
- Values: `PROVEN`, `FAILED`, `INCOMPLETE`
- `PROVEN`: all static analysis fields are empty AND all runtime assertions are true.
- `FAILED`: any field is non-empty or any assertion is false.
- `INCOMPLETE`: analysis or assertions not yet run.

## Rules

1. Proof is static analysis + test assertion. Neither alone is sufficient.
2. Static analysis operates on source code, not runtime state.
3. Runtime assertions operate on test fixtures, not live data.
4. Proof packet is generated at design time and verified at test time.
5. Proof packet is included in the hook's regression packet for diffing.
6. If proof verdict is `FAILED`, the hook MUST NOT be registered.

## Safety

- Proof packet itself has no side effects.
- Proof packet is deterministic given the same source and test fixtures.
- Proof packet does not access network, filesystem (beyond reading source), or runtime state.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
