# Runtime Governance Invariant Checker

Pure invariant checker for `RuntimeGovernanceInput`. Deterministic, no I/O, no timestamps, no network.

## API

### `check_runtime_governance_invariants(inp: RuntimeGovernanceInput) -> List[RuntimeGovernanceInvariantResult]`

Checks all 6 invariants. Returns results for each (pass and fail).

### `summarize_runtime_governance_invariants(results: List) -> Dict[str, Any]`

Returns counts: `total`, `passed`, `failed`, `errors`, `warnings`, `all_ok`.

### `invariants_to_dict(results: List) -> List[Dict]`

Serializes results to plain dicts. Deterministic output order.

### `invariants_to_markdown(results: List) -> str`

Renders results as a markdown table with summary. No timestamps.

## Invariants

| # | invariant_id | fail condition | severity |
|---|---|---|---|
| 1 | no_submit_outside_test_or_testnet | `allow_submit=True` and env not in (test, testnet) | error |
| 2 | no_network_without_explicit_mode | `allow_network=True` and `mode=""` | error |
| 3 | mode_must_be_known | `mode` not in `ALLOWED_MODES` | error |
| 4 | adapter_id_required | `adapter_id` empty | error |
| 5 | run_id_required | `run_id` empty | error |
| 6 | file_io_default_false_for_shadow | `mode=shadow` and `allow_file_io=True` | warning |

## Determinism

All functions are pure. Output is fully deterministic given the same input. No timestamps, no randomness, no I/O side effects.
