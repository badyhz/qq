# PRD 500 Backlog Execution Windows

**Task:** T910
**Module:** `core/prd_500_backlog_execution_windows.py`
**Tests:** `tests/unit/test_prd_500_backlog_execution_windows.py`

## Purpose

Split a 500+ task backlog into execution windows suitable for agent dispatch. Groups by milestone_id, then splits into risk-appropriate chunks.

## Window Size Rules

| Risk Level | Window Size | Max Parallel Agents | Route | Human Review |
|------------|-------------|---------------------|-------|--------------|
| LOW        | 20-50       | 8                   | mimo2.5pro or mimo2.5 | No |
| MEDIUM     | 20-50       | 6                   | mimo2.5pro | No |
| HIGH       | 3-15        | 3                   | mimo2.5pro with human review | Yes |
| FROZEN     | 0           | 0                   | HUMAN_ONLY | Yes |

## Key Behavior

- Every window has `hard_stop_task_id == end_task_id`
- FROZEN milestones produce a single window with 0 executable tasks
- Dominant risk: highest risk in chunk wins (FROZEN > HIGH > MEDIUM > LOW)
- Pure deterministic: no I/O, no timestamps, no random

## API

```python
build_prd_500_execution_windows(backlog: PrdBacklog) -> List[Prd500ExecutionWindow]
execution_windows_to_dict(window) -> dict
execution_windows_to_markdown(window) -> str
summarize_execution_windows(windows) -> dict
```
