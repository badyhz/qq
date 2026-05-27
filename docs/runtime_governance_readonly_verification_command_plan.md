# T851 — Runtime Governance Read-Only Verification Command Plan

## Purpose

Static, deterministic verification command plan for read-only governance layer.
Pure functions, no I/O, no timestamps, no randomness.

## Commands

| # | Command ID | Command | Purpose | Required |
|---|------------|---------|---------|----------|
| 1 | readonly-tests | `python3 -m pytest tests/unit/test_runtime_governance_readonly_* -v` | Run all read-only layer tests | yes |
| 2 | runtime-governance-tests | `python3 -m pytest tests/unit/test_runtime_governance_* -v` | Run all runtime governance tests | yes |
| 3 | governance-failure-tests | `python3 -m pytest tests/unit/test_governance_failure_* -v` | Run governance failure taxonomy tests | yes |
| 4 | core-regression | `python3 -m pytest tests/unit/test_execution.py tests/unit/test_risk_manager.py tests/unit/test_order_manager.py tests/unit/test_signal_engine.py -v` | Run core regression tests | yes |
| 5 | full-readonly-bundle | `python3 -m pytest tests/unit/test_runtime_governance_readonly_* tests/unit/test_runtime_governance_* tests/unit/test_governance_failure_* -q` | Run full readonly + governance bundle | no |

## API

- `build_readonly_verification_command_plan() -> List[RuntimeGovernanceReadOnlyVerificationCommand]`
- `readonly_verification_command_plan_to_dict(commands) -> List[Dict]`
- `readonly_verification_command_plan_to_markdown(commands) -> str`

## Dataclass

`RuntimeGovernanceReadOnlyVerificationCommand(frozen=True)` with fields:
- `command_id: str`
- `command: str`
- `purpose: str`
- `required: bool`
