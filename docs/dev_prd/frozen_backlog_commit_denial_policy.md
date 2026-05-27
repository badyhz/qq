# Frozen Backlog Commit Denial Policy

**Task:** T1264
**Status:** release_hold = HOLD
**Scope:** All 22 frozen backlog files

## Purpose

Define explicit commit denial rules for frozen backlog items.
No frozen file may enter the tracked repository without gate clearance.

## Denial Rules

### Automatic Denial Triggers

1. File is in frozen backlog inventory (HIGH or MEDIUM)
2. release_hold state is HOLD
3. No human approval artifact exists (T1266)
4. Evidence packet incomplete (T1267)
5. Promotion boundary not satisfied (T1268)

### Denial Workflow

1. Agent attempts git add / git commit
2. Pre-commit hook checks frozen inventory
3. If file matches frozen pattern AND no approval exists:
   - Commit blocked
   - Denial reason logged
   - Agent notified of required gates

### Override Conditions

- Human explicitly approves promotion (T1266)
- All evidence requirements met (T1267)
- Promotion boundary validated (T1268)
- Rollback plan documented (T1269)

## Denial Record Format

```
DENIED: <filename>
REASON: <denial_trigger>
REQUIRED: <missing_gate>
TIMESTAMP: <ISO8601>
```

## Enforcement

- Pre-commit hook enforces denial at git level
- Agent rules enforce denial at workflow level
- No workaround permitted without human override
