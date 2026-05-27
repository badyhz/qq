# Human Approval Command Transcript Policy

**Task ID:** T1295
**release_hold:** HOLD

## Purpose

Defines what commands must be recorded in an approval evidence pack.
Ensures full traceability of actions taken against frozen files.

## Required Transcript Entries

Every command that touches a target frozen file MUST be recorded:

- File reads (cat, head, tail, grep on frozen files)
- File writes (edit, sed, tee on frozen files)
- File moves (mv, rename of frozen files)
- Status checks (git status, ls on frozen files)
- Diff operations (git diff on frozen files)

## Transcript Format

Each entry MUST contain:

| Field | Description |
|-------|-------------|
| command | Exact command string executed |
| timestamp | When command was executed (ISO 8601) |
| exit_code | Command exit code |
| files_affected | List of frozen file paths |
| output_hash | SHA-256 of command output (truncated to 16 chars) |

## Exclusions

The following are NOT recorded in transcript:

- Commands unrelated to frozen files
- Internal tool calls that do not access frozen files
- Commands executed in unrelated directories

## Validation

- Transcript entries MUST be contiguous (no gaps in sequence)
- Each entry timestamp MUST be between pack_created and review_started
- Command strings MUST be verbatim — no paraphrasing
- exit_code MUST be captured at time of execution

## Integrity

- Transcript is append-only during pack lifecycle
- No entry may be deleted or modified after capture
- No entry may reference commands not executed
- No entry may omit commands that were executed

## Constraints

- Transcript MUST be complete — missing entries invalidate pack
- No transcript compression or summarization
- No transcript redaction (redaction = rejection)
- release_hold = HOLD — transcript does not grant release
