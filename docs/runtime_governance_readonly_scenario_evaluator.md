# T834 — Runtime Governance Read-Only Scenario Evaluator

## Purpose

Evaluates read-only scenarios through permission envelopes and invariants.
Deterministic, pure, no I/O.

## Module

`core/runtime_governance_readonly_scenario_evaluator.py`

## Dataclass

`RuntimeGovernanceReadOnlyScenarioEvaluation` (frozen=True):
- `scenario_id`: str
- `expected_verdict`: str
- `actual_verdict`: str
- `expected_blocked`: bool
- `actual_blocked`: bool
- `ok`: bool — True if actual_verdict matches expected_verdict
- `notes`: List[str] — invariant check results

## Functions

| Function | Signature | Purpose |
|---|---|---|
| `evaluate_readonly_scenario` | scenario -> Evaluation | Evaluate single scenario |
| `evaluate_readonly_scenario_catalog` | () -> List[Evaluation] | Evaluate all 6 scenarios |
| `readonly_evaluations_to_dict` | evaluations -> List[Dict] | Serialize |
| `readonly_evaluations_to_markdown` | evaluations -> str | Render markdown table |

## Evaluation Flow

1. Build permission envelope from scenario's `permission_envelope_kind`
2. Evaluate envelope verdict via `evaluate_permission_envelope_raw`
3. Check invariants via `check_readonly_permission_invariants`
4. `ok = actual_verdict == expected_verdict`

## Scenario Catalog (6 scenarios)

| scenario_id | envelope_kind | expected |
|---|---|---|
| safe_summary_read | account_summary_read | PASS |
| unsafe_network | network_egress | BLOCKED |
| unsafe_write | filesystem_write | BLOCKED |
| unsafe_order | order_submit | BLOCKED |
| unsafe_secret | secret_access | BLOCKED |
| unsafe_account_mutation | account_mutation | BLOCKED |
