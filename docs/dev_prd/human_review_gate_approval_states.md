# Human Review Gate Approval States

## State Machine

```
PENDING_APPROVAL ──┬──> APPROVED
                   ├──> APPROVED_WITH_CONDITIONS
                   └──> APPROVAL_EXPIRED
```

## States

### PENDING_APPROVAL

**Description:** Gate created, awaiting human decision. No action may proceed.

**Entry:** Gate initialized with required evidence checklist.

**Exit conditions:**
- Human issues APPROVE -> transitions to APPROVED
- Human issues CONDITIONAL_APPROVE -> transitions to APPROVED_WITH_CONDITIONS
- No decision within allowed window -> transitions to APPROVAL_EXPIRED

### APPROVED

**Description:** Human has explicitly approved. Action may proceed.

**Entry:** Human issues APPROVE decision with all evidence verified.

**Exit conditions:**
- Action completes -> gate closes
- Action fails -> gate reopens to PENDING_APPROVAL

### APPROVED_WITH_CONDITIONS

**Description:** Human has approved with specific conditions attached. Action may proceed only after conditions verified.

**Entry:** Human issues CONDITIONAL_APPROVE with documented conditions.

**Exit conditions:**
- All conditions verified met -> equivalent to APPROVED
- Conditions not met within scope -> transitions to APPROVAL_EXPIRED
- Human issues REJECT -> transitions to rejection states

### APPROVAL_EXPIRED

**Description:** Approval window closed without decision or conditions not met. Terminal state for this approval cycle.

**Entry:** Timeout reached or condition deadline passed.

**Exit conditions:**
- New gate cycle initiated -> fresh PENDING_APPROVAL
- No further action without new gate creation

## Transitions

| From | To | Trigger |
|------|-----|---------|
| PENDING_APPROVAL | APPROVED | Human APPROVE decision |
| PENDING_APPROVAL | APPROVED_WITH_CONDITIONS | Human CONDITIONAL_APPROVE decision |
| PENDING_APPROVAL | APPROVAL_EXPIRED | Timeout / condition deadline |
| APPROVED_WITH_CONDITIONS | APPROVED | All conditions verified |
| APPROVED_WITH_CONDITIONS | APPROVAL_EXPIRED | Conditions not met in time |
