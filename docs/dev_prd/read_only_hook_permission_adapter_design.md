# Read-Only Hook Permission Adapter Design

## Purpose

Define how external permissions (from config, caller context, or frozen state) are mapped to internal read-only flags consumed by the hook system.

## Contract

```yaml
adapter:
  input: permission_envelope (from input contract)
  output: internal_permission_flags (list of read-only flags)
  behavior: mapping-only, no escalation
```

## Fields / Items

### Input: permission_envelope
- Source fields: `granted_flags`, `source`, `expiry`
- See `read_only_hook_input_contract.md` for definitions.

### Output: internal_permission_flags
- Type: `list` of `string`
- Allowed flags:
  - `RO_QUERY` — may read structured data
  - `RO_VALIDATE` — may run validation logic
  - `RO_INSPECT` — may inspect internal state copies
  - `RO_AUDIT` — may run audit checks
  - `RO_SNAPSHOT` — may take point-in-time snapshots
- No write flags exist in the read-only namespace.

### Mapping Logic
- Adapter reads `granted_flags` from envelope.
- Adapter filters to only recognized read-only flags.
- Adapter checks `source` and `expiry`.
- If `source == "FROZEN"`: output is `[RO_QUERY]` only. All other flags stripped.
- If `expiry` is set and expired: output is `[]` (empty).
- Adapter NEVER adds flags not present in input.

## Rules

1. Adapter cannot escalate permissions. Output is always a subset of input.
2. FROZEN source blocks all flags except `RO_QUERY`.
3. Unknown flags in input are silently dropped, not escalated.
4. Adapter is a pure function: same input = same output.
5. No I/O in adapter logic.
6. Adapter output is logged in evidence record for audit.

## Safety

- If adapter fails to parse input, result is `[]` (no permissions), not a default set.
- Adapter has no access to runtime state, environment variables, or secrets.
- Adapter does not cache permissions across invocations.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
