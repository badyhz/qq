# PRD 500 Backlog Human Gate Pack

T914. Pure deterministic. No I/O. No timestamps. No random.

## Purpose

Defines mandatory human approval gates that block execution of 500-backlog tasks until explicit human authorization is granted.

## Gates

| Gate ID | Applies To | Condition | Required |
|---|---|---|---|
| GATE-HIGH-RISK | HIGH risk windows | any HIGH risk task exists | Yes |
| GATE-FROZEN | FROZEN domains | any FROZEN risk task exists | Yes |
| GATE-RUNTIME-INTEGRATION | runtime integration review | any runtime integration task exists | Yes |
| GATE-HOOK-IMPLEMENTATION | hook implementation review | any hook implementation task exists | Yes |
| GATE-LIVE-EXECUTION | live execution discussion | always blocked | Yes |
| GATE-PLANNER-AUTONOMOUS | planner autonomous execution | always blocked | Yes |

## Approval Options

All gates accept: `approve`, `reject`, `defer`, `request_changes`.

## Module

`core/prd_500_backlog_human_gate_pack.py`

### API

- `build_prd_500_human_gate_pack(backlog) -> List[Prd500HumanGate]`
- `human_gate_pack_to_dict(gate) -> dict`
- `human_gate_pack_to_markdown(gate) -> str`

## Safety

- GATE-LIVE-EXECUTION and GATE-PLANNER-AUTONOMOUS are **always blocked** — condition is `"always blocked"`, not data-dependent.
- Gate set is hardcoded minimum. Backlog parameter accepted for future extension but does not alter output in current version.
