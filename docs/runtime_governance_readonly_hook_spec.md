# Runtime Governance Read-Only Hook Spec

T826 — runtime governance read-only hook specification.

## Purpose

Define a read-only hook contract for runtime governance inspection. The hook can observe system state but cannot mutate it.

## Forbidden Side Effects

All six are mandatory:

1. order placement
2. account mutation
3. credential access
4. network call
5. file write
6. planner action

## Allowed Inputs

- current positions
- open orders
- account balance
- risk parameters
- market data snapshot
- guard definitions
- governance rules

## Forbidden Inputs

- private keys
- api secrets
- session tokens

## Allowed Outputs

- diagnostic summary
- guard violation report
- state snapshot
- rule evaluation result
- compliance status

No live/action language (submit, execute, place order, buy, sell, etc.) permitted in allowed outputs.

## Required Guards

- dry_run_enforced
- no_order_submission
- no_credential_access
- no_network_egress
- no_file_mutation

## Spec Contract

- `build_runtime_governance_readonly_hook_spec()` — pure, deterministic builder
- `readonly_hook_spec_to_dict(spec)` — deterministic serialization
- `readonly_hook_spec_to_markdown(spec)` — deterministic markdown

All functions are pure. Dataclass is frozen. Repeated calls return identical results.

## Module

`core/runtime_governance_readonly_hook_spec.py`

## Tests

`tests/unit/test_runtime_governance_readonly_hook_spec.py`
