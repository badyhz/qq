# Runtime Governance Scenario Batch Evaluator

Evaluates every scenario in the runtime governance scenario catalog by building its preflight packet and comparing actual verdict/proceed against expected values.

## Module

`core.runtime_governance_scenario_batch_evaluator`

## Dataclass

```python
@dataclass(frozen=True)
class RuntimeGovernanceScenarioEvaluation:
    scenario_id: str
    expected_verdict: str
    actual_verdict: str
    expected_ready_for_runtime: bool
    actual_ready_for_runtime: bool
    ok: bool
    notes: List[str]
```

`ok=True` only when both `actual_verdict == expected_verdict` AND `actual_ready_for_runtime == expected_ready_for_runtime`.

## Functions

| Function | Signature | Description |
|---|---|---|
| `evaluate_runtime_governance_scenario` | `(scenario) -> RuntimeGovernanceScenarioEvaluation` | Evaluate one scenario through preflight packet builder |
| `evaluate_runtime_governance_scenario_catalog` | `(catalog=None) -> List[RuntimeGovernanceScenarioEvaluation]` | Evaluate all scenarios (default = full 8-scenario catalog) |
| `scenario_evaluations_to_dict` | `(evaluations) -> List[Dict]` | Serialize to plain dicts |
| `scenario_evaluations_to_markdown` | `(evaluations) -> str` | Render as Markdown table |

## Dependencies

- `core.runtime_governance_scenario_catalog` — `build_runtime_governance_scenario_catalog`, `RuntimeGovernanceScenario`
- `core.runtime_governance_preflight_packet` — `build_runtime_governance_preflight_packet`

## Usage

```python
from core.runtime_governance_scenario_batch_evaluator import (
    evaluate_runtime_governance_scenario_catalog,
    scenario_evaluations_to_dict,
    scenario_evaluations_to_markdown,
)

evaluations = evaluate_runtime_governance_scenario_catalog()
all_ok = all(e.ok for e in evaluations)

as_dict = scenario_evaluations_to_dict(evaluations)
as_md = scenario_evaluations_to_markdown(evaluations)
```

## Tests

```
python3 -m pytest tests/unit/test_runtime_governance_scenario_batch_evaluator.py -v
```
