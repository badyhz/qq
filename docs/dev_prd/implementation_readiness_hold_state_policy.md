# T1194 - Implementation Readiness Hold State Policy

## States

### HOLD_CLEAR
- No blockers present
- All dimensions above threshold
- Ready for next action

### HOLD_PENDING_REVIEW
- Human review required
- Evidence collected but not approved
- Blocks until reviewer acts

### HOLD_BLOCKED
- Active blockers present
- Cannot proceed until blockers resolved
- Blocker resolution tracked

### HOLD_FROZEN
- Explicitly frozen by authority
- No modifications allowed
- Only unfreeze by same or higher authority

## Transitions

```
CLEAR -> PENDING_REVIEW:  human gate triggered
PENDING_REVIEW -> CLEAR:  human approves
PENDING_REVIEW -> BLOCKED: human rejects
BLOCKED -> CLEAR:         all blockers resolved
CLEAR -> FROZEN:          authority freeze
FROZEN -> CLEAR:          authority unfreeze
BLOCKED -> FROZEN:        authority freeze
```

## Exit Criteria

| State | Exit Condition |
|---|---|
| PENDING_REVIEW | Human approval with evidence |
| BLOCKED | All blockers resolved and verified |
| FROZEN | Authority unfreeze |
| CLEAR | Ready to proceed |
