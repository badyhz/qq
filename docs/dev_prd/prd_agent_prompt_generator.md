# PRD Agent Prompt Generator — T868

## Purpose

Generate short agent prompts from PRD task ranges.

## Module

`core/prd_agent_prompt_generator.py`

## Dataclass

### PrdAgentPrompt (frozen=True)

| Field | Type | Description |
|-------|------|-------------|
| task_range | str | Range string (e.g. "T100..T105") |
| prompt_text | str | Full prompt text |
| required_docs | List[str] | Docs to read before starting |
| hard_stop_task_id | str | Last task ID (hard stop) |
| safety_warnings | List[str] | Safety warnings |
| notes | List[str] | Notes from tasks |

## Functions

### generate_agent_prompt_for_task_range(tasks, start_task_id, end_task_id, required_docs) -> PrdAgentPrompt

Generates agent prompt for a task range.

**Constraints:**
- Pure, deterministic
- No I/O, no timestamps, no random

**Prompt includes:**
- Caveman / terse engineering mode
- Output format: FILES / TESTS / COMMITS / RESULT / NOTES
- Required docs
- Task range (start..end)
- Allowed files per task
- Acceptance commands
- Safety rules (frozen modules, no live trading, etc.)
- Hard stop after end_task_id

### prd_agent_prompt_to_dict(prompt) -> Dict

Convert PrdAgentPrompt to dict.

### prd_agent_prompt_to_markdown(prompt) -> str

Convert PrdAgentPrompt to markdown string.

## Usage

```python
from core.prd_task_model import PrdTask
from core.prd_agent_prompt_generator import (
    generate_agent_prompt_for_task_range,
    prd_agent_prompt_to_dict,
    prd_agent_prompt_to_markdown,
)

tasks = [
    PrdTask(
        task_id="T100",
        title="Implement feature X",
        status="NOT_STARTED",
        allowed_files=["core/foo.py"],
        dependencies=[],
        acceptance_commands=["python3 -m pytest tests/unit/test_foo.py -v"],
        risk_level="LOW",
        notes=[],
    ),
]

prompt = generate_agent_prompt_for_task_range(
    tasks=tasks,
    start_task_id="T100",
    end_task_id="T100",
    required_docs=["PROJECT_STATE.md", "TASKS.md"],
)

# Get as dict
d = prd_agent_prompt_to_dict(prompt)

# Get as markdown
md = prd_agent_prompt_to_markdown(prompt)
```

## Tests

```bash
python3 -m pytest tests/unit/test_prd_agent_prompt_generator.py -v
```
