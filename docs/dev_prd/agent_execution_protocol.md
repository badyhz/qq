# Agent Execution Protocol

## Purpose

This document is the primary protocol future agents must read before executing repo tasks. It defines execution behavior, output format, safety rules, commit rules, and stop conditions.

## Required Agent Output Format

Every task must produce:

```
FILES
- changed:
- added:
- deleted:

TESTS
- command:
- result:

COMMITS
- hash: message

RESULT
- PASS / PARTIAL / FAIL / BLOCKED

NOTES
- max 5 lines
- blockers only
```

## Required Behavior

1. Read relevant PRD files first.
2. Execute only assigned task IDs.
3. Modify only allowed files.
4. Commit per task when possible.
5. Stop at assigned hard stop.
6. Report PARTIAL instead of improvising.

## Permission-Safe Command Rules

- Avoid heredoc commits.
- Avoid chained `git add && git commit`.
- Use simple one-line commit messages.
- If permission denies command, report exact manual command.

## API Freeze Rule

- Do not rewrite existing module APIs to satisfy downstream tests.
- If import mismatch appears, stop that task and report PARTIAL.
- Do not refactor old modules unless explicitly authorized.
- Existing committed modules are frozen unless a human explicitly authorizes modification.

## Large File Rule

- Never load full CSV/JSONL/log files.
- Use `ls -lh`, `wc -l`, `head`, `tail`, `rg`, or chunked summaries only.

## Safety Rules

- No live trading.
- No real submit.
- No secrets.
- No account mutation.
- No planner autonomous integration.
- No network calls.
- No file I/O implementation.
- No runtime integration.

## Stop Conditions

Stop immediately if:

- unauthorized file required
- API mismatch requiring old module change
- test failure after one local fix attempt
- permission denied on critical command
- task beyond assigned range
- frozen boundary contamination
- unclear scope
- governance violation
