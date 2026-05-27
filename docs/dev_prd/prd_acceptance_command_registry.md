# PRD Acceptance Command Registry

Static registry of safe verification commands for PRD control-plane.

## Design

- Frozen dataclass `PrdAcceptanceCommand`
- Pure functions, no I/O, no timestamps, no random
- All commands safe for agent execution (no heredoc, no rm, no network)

## Registered Commands

| command_id | command | purpose | required |
|---|---|---|---|
| prd-control-plane | `python3 -m pytest tests/unit/test_dev_prd_control_plane.py -q` | Run PRD control plane tests | yes |
| readonly-glob | `python3 -m pytest tests/unit/test_runtime_governance_readonly_* -q` | Run readonly layer tests | yes |
| runtime-governance-glob | `python3 -m pytest tests/unit/test_runtime_governance_* -q` | Run runtime governance tests | yes |
| governance-failure-glob | `python3 -m pytest tests/unit/test_governance_failure_* -q` | Run governance failure tests | yes |
| order-manager | `python3 -m pytest tests/unit/test_order_manager.py -q` | Run order manager tests | yes |
| git-status | `git status --short` | Check working tree status | no |
| git-log | `git log --oneline -40` | View recent commits | no |

## API

- `build_prd_acceptance_command_registry()` -> List[PrdAcceptanceCommand]
- `acceptance_command_registry_to_dict(commands)` -> List[Dict]
- `acceptance_command_registry_to_markdown(commands)` -> str
- `summarize_acceptance_command_registry(commands)` -> Dict
