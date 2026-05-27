# Runtime Governance Sample Factory

Pure sample object factory for runtime governance types. Deterministic. No I/O.

## Module

`core/runtime_governance_sample_factory.py`

## API

| Function | Returns | Description |
|---|---|---|
| `build_runtime_governance_sample_input(kind)` | `RuntimeGovernanceInput` | Sample input for kind |
| `build_runtime_governance_sample_preflight_packet(kind)` | `RuntimeGovernancePreflightPacket` | Sample preflight packet for kind |
| `build_runtime_governance_sample_markdown(kind)` | `str` | Deterministic markdown rendering for kind |

All functions raise `ValueError` for unsupported kinds.

## Kinds

| Kind | Mode | Verdict | Proceed | Description |
|---|---|---|---|---|
| `pass` | shadow | PASS | True | Valid shadow input, all checks pass |
| `fail` | shadow | FAIL | False | Missing run_id, validation failure |
| `blocked` | shadow | BLOCKED | False | allow_submit=True in prod, policy block |
| `warn_like` | dry_run | PASS | True | Valid dry_run input, closest to warn in pure contract |
| `invalid_contract` | unknown_mode | FAIL | False | Unknown mode, validation failure |

## Determinism

All functions are pure. Calling the same function with the same kind always returns structurally identical output. No timestamps, no random, no I/O.

## Dependencies

- `core.runtime_governance_contract` — RuntimeGovernanceInput, normalize_runtime_governance_input
- `core.runtime_governance_preflight_packet` — RuntimeGovernancePreflightPacket, build_runtime_governance_preflight_packet, preflight_packet_to_markdown

## Tests

`tests/unit/test_runtime_governance_sample_factory.py`

```bash
python3 -m pytest tests/unit/test_runtime_governance_sample_factory.py -v
```
