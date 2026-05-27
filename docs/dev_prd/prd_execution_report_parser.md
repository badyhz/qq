# T871 — PRD Execution Report Parser

## Purpose

Parse agent final execution reports into structured `PrdExecutionReport` dataclass.

## API

### `parse_prd_execution_report(report_text: str) -> PrdExecutionReport`

Extracts five sections (FILES, TESTS, COMMITS, RESULT, NOTES) from raw text.

- `parsed_ok = True` only when all sections present AND result in {PASS, PARTIAL, FAIL, BLOCKED}
- `result` normalized to uppercase
- `missing_sections` lists any absent section names

### `execution_report_to_dict(report) -> Dict`

Flattens dataclass to plain dict (JSON-safe).

### `execution_report_to_markdown(report) -> str`

Renders structured report as markdown with section headers.

### `summarize_execution_report(report) -> Dict`

Compact summary: parsed_ok, result, missing_sections, has_* booleans.

## Constraints

- Pure, deterministic
- No I/O, no timestamps, no random
- Frozen dataclass

## Expected Report Format

```
FILES
- path/to/file.py

TESTS
- command: pytest
- result: PASS

COMMITS
- abc1234 feat: description

RESULT
PASS

NOTES
- any notes
```
