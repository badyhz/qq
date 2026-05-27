# T1168 - Untracked Freeze Ledger: Stale File Policy

## Definition

A file is considered **stale** when:
- It has been in NEW state in the ledger.
- It has not been modified for N consecutive days (default N=30).
- No operator action has been recorded for it during that period.

## Detection

- On each ledger scan, compare file modification time against the last recorded observation.
- If days since last modification >= N, transition state from NEW to STALE.
- Record the transition in the ledger with the stale duration.

## Actions

### Flag
- Mark the file with state=STALE in the ledger.
- Record `days_stale` and `last_modified_slot` in the ledger entry.

### Escalate
- If a HIGH risk file becomes stale, generate an immediate alert.
- If any file remains stale for 2*N days (default 60 days), escalate to operator.
- Escalation includes: file path, risk class, days stale, recommended action.

### Archive Suggestion
- For LOW risk stale files, recommend archiving (move to archive directory or delete).
- For MEDIUM risk stale files, recommend human review before archiving.
- For HIGH risk stale files, never recommend auto-archive; require human decision.

## Recommended Actions by Risk Class

| Risk Class | Stale < 2N          | Stale >= 2N                  |
|------------|---------------------|------------------------------|
| HIGH       | Alert, hold         | Escalate, block all actions  |
| MEDIUM     | Flag, recommend review | Escalate, recommend archive |
| LOW        | Flag                | Recommend archive or delete  |

## Reset Condition

- If a stale file is modified (content hash changes), reset state to NEW.
- The stale counter resets; the file re-enters the normal classification flow.
