# Read-Only Hook Prompt Pack

## Purpose

Define the prompt template for the next agent tasked with implementing or reviewing the read-only hook system. The prompt enforces caveman mode, documentation-first workflow, and hard stops on forbidden actions.

## Contract

The prompt pack is a structured instruction set. The receiving agent must follow it verbatim. Deviations from the prompt are not permitted.

## Fields / Items

| Section | Content |
|---------|---------|
| Mode | Caveman — terse, no filler, technical accuracy |
| Pre-read | Read all docs in `docs/dev_prd/read_only_hook_*.md` before any action |
| Tasks | Execute only tasks listed in the current task file |
| Hard stop | No live trading, no submit, no exchange, no secrets, no planner |
| Output | Follow project report format: FILES, TESTS, RESULT, NOTES |

## Rules

1. Agent must read documentation before executing any task.
2. Agent must operate in caveman mode — no greetings, no filler.
3. Agent must stop at the hard stop boundary — no exceptions.
4. Agent must not create files outside the approved task list.
5. Agent must not modify control files without explicit instruction.

## Safety

- Prompt pack is the authority for agent behavior.
- Hard stops are non-negotiable.
- Any violation of the prompt pack is a blocking issue.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
