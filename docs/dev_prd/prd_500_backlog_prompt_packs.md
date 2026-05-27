# PRD 500 Backlog Prompt Packs (T911)

Splits a 500-task backlog into deterministic 25-task prompt packs.

## File

`core/prd_500_backlog_prompt_packs.py`

## Dataclass

`Prd500PromptPack` — frozen, contains pack_id, window_id, task_range, prompt_text, hard_stop_task_id, required_docs, safety_warnings, notes.

## Functions

- `build_prd_500_prompt_packs(backlog, required_docs=None)` — returns list of packs
- `prompt_packs_to_dict(pack)` — serialize to dict
- `prompt_packs_to_markdown(pack)` — serialize to markdown
- `summarize_prompt_packs(packs)` — summary stats

## Prompt pack includes

- Caveman / terse engineering mode instruction
- Output format: FILES / TESTS / COMMITS / RESULT / NOTES
- Required docs list
- Task range and hard stop
- Forbidden areas: live trading, submit, planner, exchange, secrets, runtime execution

## Defaults

- Pack size: 25 tasks
- Required docs: `agent_execution_protocol.md`, `runtime_governance_safety_boundaries.md`
- Safety warnings: no live trading, no real orders, no secrets, no planner autonomous execution
