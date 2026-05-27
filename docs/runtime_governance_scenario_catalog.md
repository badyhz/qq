# Runtime Governance Scenario Catalog

## Overview

Deterministic scenario definitions for runtime governance preflight testing.
No I/O, no timestamps, no randomness. Pure data and pure functions.

Module: `core.runtime_governance_scenario_catalog`

## API

### Dataclass

```python
@dataclass(frozen=True)
class RuntimeGovernanceScenario:
    scenario_id: str
    name: str
    input: RuntimeGovernanceInput
    expected_verdict: str  # PASS / FAIL / BLOCKED
    expected_ready_for_runtime: bool
    tags: List[str]  # sorted
    notes: str
```

### Functions

| Function | Returns | Notes |
|---|---|---|
| `build_runtime_governance_scenario_catalog()` | `List[RuntimeGovernanceScenario]` | Full 8-item catalog |
| `get_runtime_governance_scenario(scenario_id)` | `RuntimeGovernanceScenario` | Raises `ValueError` if not found |
| `scenario_catalog_to_dict(catalog)` | `List[Dict]` | Deterministic serialization |
| `scenario_catalog_to_markdown(catalog)` | `str` | Markdown table |

## Scenario List

| scenario_id | name | mode | verdict | ready | tags |
|---|---|---|---|---|---|
| valid_shadow | Valid shadow run | shadow | PASS | True | shadow, valid |
| valid_dry_run | Valid dry run | dry_run | PASS | True | dry_run, valid |
| missing_run_id | Missing run_id | shadow | FAIL | False | fail, validation |
| missing_adapter_id | Missing adapter_id | shadow | FAIL | False | fail, validation |
| submit_blocked_prod | Submit blocked in prod | shadow | BLOCKED | False | blocked, policy |
| network_blocked_without_explicit_mode | Network without explicit mode | (empty) | BLOCKED | False | blocked, policy |
| unknown_mode | Unknown mode value | bogus | FAIL | False | fail, validation |
| blocked_policy | Shadow with submit in prod | shadow | BLOCKED | False | blocked, policy |

## Verdict Mapping

- **PASS** -- `validate_runtime_governance_input` returns `ok=True`
- **FAIL** -- validation failures (missing fields, unknown mode)
- **BLOCKED** -- policy blocks (submit in non-test env, network without mode)

## Determinism Notes

- Scenario list order is fixed (8 items).
- `tags` are always sorted.
- `scenario_catalog_to_dict` produces identical output on every call.
- `scenario_catalog_to_markdown` produces identical output on every call.
- `build_runtime_governance_scenario_catalog` returns fresh copies each call but with identical content.
