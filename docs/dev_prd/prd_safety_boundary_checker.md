# PRD Safety Boundary Checker — T870

## Purpose
Check proposed allowed files and task text against safety boundaries before PRD tasks proceed.

## Module
`core/prd_safety_boundary_checker.py`

## Data Classes

### PrdSafetyBoundaryIssue (frozen)
| Field | Type | Description |
|-------|------|-------------|
| issue_id | str | Unique issue identifier |
| severity | str | "blocker" or "warning" |
| category | str | blocked_path, term_blocker, term_warning |
| target | str | File path or term that triggered |
| message | str | Human-readable description |

### PrdSafetyBoundaryReport (frozen)
| Field | Type | Description |
|-------|------|-------------|
| checked_items | int | Total items checked (files + task text) |
| issue_count | int | Total issues found |
| blocker_count | int | Number of blocker-severity issues |
| final_verdict | str | PASS, WARN, or BLOCKED |
| issues | tuple | Tuple of PrdSafetyBoundaryIssue |
| notes | tuple | Tuple of advisory strings |

## API

```python
check_prd_safety_boundaries(task_text: str, allowed_files: List[str]) -> PrdSafetyBoundaryReport
safety_boundary_report_to_dict(report) -> Dict
safety_boundary_report_to_markdown(report) -> str
```

## Blocked Path Substrings
Any allowed file path containing these substrings triggers a BLOCKER:
- scripts/submit
- live_runner
- exchange_client
- binance_testnet_client
- secrets
- .env
- credentials
- planner
- account
- order placement live path

## Warning Terms in Task Text
These terms in task_text trigger a check:
- live trading
- real order
- submit
- API key
- secret
- exchange connection
- planner autonomous

If negation context ("forbidden", "do not", "no", "frozen", "never", "must not", "prohibited", "disallowed") appears within ~80 chars of the term, severity is downgraded to warning. Otherwise it is a blocker.

## Verdict Logic
- Any blocker-severity issue → BLOCKED
- Only warning-severity issues → WARN
- No issues → PASS

## Properties
- Pure, deterministic
- No I/O, no timestamps, no random
- All dataclasses frozen

## Tests
`tests/unit/test_prd_safety_boundary_checker.py`
- safe docs/dev_prd files → PASS
- submit script path → BLOCKED
- .env file → BLOCKED
- planner path → BLOCKED
- forbidden term with "do not" context → warning, not blocker
- deterministic output
