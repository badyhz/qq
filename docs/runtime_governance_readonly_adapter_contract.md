# T827 — Runtime Governance Read-Only Adapter Contract

## Purpose

Defines the input/output contract for read-only adapter views in the runtime governance layer. Adapters expose sanitized, non-actionable views of runtime state. No mutations, no network I/O.

## Types

### RuntimeGovernanceReadOnlyAdapterInput (frozen dataclass)

| Field           | Type             | Required | Notes                        |
|-----------------|------------------|----------|------------------------------|
| adapter_id      | str              | yes      | non-empty                    |
| run_id          | str              | yes      | non-empty                    |
| mode            | str              | yes      | dry-run, live, shadow, paper |
| requested_view  | str              | yes      | summary, positions, orders, risk |
| symbols         | List[str]        | yes      | non-empty                    |
| metadata        | Dict[str, Any]   | no       | default {}                   |

### RuntimeGovernanceReadOnlyAdapterOutput (frozen dataclass)

| Field              | Type             | Notes                    |
|--------------------|------------------|--------------------------|
| ok                 | bool             | success flag             |
| view_name          | str              | echo of requested view   |
| sanitized_payload  | Dict[str, Any]   | non-actionable data      |
| failure_codes      | List[str]        | empty on success         |
| notes              | List[str]        | advisory, default []     |

## Functions

- `build_readonly_adapter_input_sample(kind)` — factory for test fixtures. Kinds: `valid_summary`, `missing_adapter`, `invalid_mode`, `empty_symbols`.
- `validate_readonly_adapter_input(inp)` — pure validation, returns bool.
- `readonly_adapter_input_to_dict(inp)` — serialize input.
- `readonly_adapter_output_to_dict(out)` — serialize output.

## Safety

- All dataclasses are frozen — no mutation after construction.
- Validation is pure — no I/O, no side effects.
- Samples are for testing only — not for production use.

## Tests

```
python3 -m pytest tests/unit/test_runtime_governance_readonly_adapter_contract.py -v
```
