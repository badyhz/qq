# Runtime Governance Input Contract (T794)

Pure data contract for runtime governance checks. Not runtime integration.

## Dataclasses

### RuntimeGovernanceInput

| Field | Type | Description |
|---|---|---|
| run_id | str | Unique run identifier |
| adapter_id | str | Adapter identifier |
| mode | str | Operating mode |
| requested_action | str | Action being requested |
| symbol | str | Trading symbol |
| environment | str | Deployment environment |
| allow_network | bool | Network access flag |
| allow_submit | bool | Order submission flag |
| allow_file_io | bool | File I/O flag |
| metadata | dict | Arbitrary metadata |

### RuntimeGovernanceContractResult

| Field | Type | Description |
|---|---|---|
| ok | bool | Whether input passed all checks |
| failures | list[GovernanceFailure] | Validation/policy failures |
| normalized_input | RuntimeGovernanceInput or None | Input if valid |
| notes | list[str] | Human-readable notes |

## Functions

- `normalize_runtime_governance_input(**kwargs)` — Build input from loose kwargs
- `validate_runtime_governance_input(inp)` — Validate against policy rules
- `runtime_governance_input_to_dict(inp)` — Serialize to plain dict

## Validation Rules

1. Missing `run_id` => VALIDATION_FAILURE
2. Missing `adapter_id` => VALIDATION_FAILURE
3. Unknown `mode` => VALIDATION_FAILURE (allowed: shadow, dry_run, testnet_dry, testnet_submit_simulated)
4. `allow_submit=True` in non-test environment => POLICY_BLOCK
5. `allow_network=True` without explicit mode => POLICY_BLOCK

## Constraints

- Deterministic: no timestamps, no random, no environment reads
- No file I/O
- No network
- No live system dependency
