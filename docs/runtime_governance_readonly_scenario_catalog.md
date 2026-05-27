# T831 — Read-Only Scenario Catalog

Catalog of 6 scenarios for runtime governance read-only boundary testing.

## Scenarios

| scenario_id | description | envelope_kind | verdict | blocked | tags |
|---|---|---|---|---|---|
| safe_summary_read | Read account summary — safe read-only operation | account_summary_read | PASS | False | safe, read |
| unsafe_network | Outbound network call — violates read-only boundary | network_egress | BLOCKED | True | unsafe, network |
| unsafe_write | Filesystem write — violates read-only boundary | filesystem_write | BLOCKED | True | unsafe, write |
| unsafe_order | Order submission — violates read-only boundary | order_submit | BLOCKED | True | unsafe, order |
| unsafe_secret | Secret/credential access — violates read-only boundary | secret_access | BLOCKED | True | unsafe, secret |
| unsafe_account_mutation | Account state mutation — violates read-only boundary | account_mutation | BLOCKED | True | unsafe, mutation |

## Module

`core/runtime_governance_readonly_scenario_catalog.py`

- `build_readonly_scenario_catalog()` — returns full catalog (6 scenarios)
- `get_readonly_scenario(scenario_id)` — lookup by id, raises ValueError if missing
- `readonly_scenario_catalog_to_dict(catalog)` — serialize to list of dicts
- `readonly_scenario_catalog_to_markdown(catalog)` — deterministic markdown table

## Tests

`tests/unit/test_runtime_governance_readonly_scenario_catalog.py`

- All 6 scenarios present in correct order
- All unsafe scenarios have verdict BLOCKED
- Unknown scenario_id raises ValueError
- All outputs deterministic across repeated calls
- Serialization round-trip correct
