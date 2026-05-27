# Human Review Gate Rejection States

## State Machine

```
PENDING_REVIEW ──┬──> REJECTED
                 ├──> REJECTED_PERMANENTLY
                 └──> REJECTED_WITH_REVISION_ALLOWED
```

## States

### PENDING_REVIEW

**Description:** Gate is under review. No rejection yet. Same entry as PENDING_APPROVAL — the gate awaits human decision.

**Entry:** Gate initialized, human review not yet complete.

**Exit conditions:**
- Human issues REJECT -> transitions to REJECTED
- Human issues REJECT with permanent flag -> transitions to REJECTED_PERMANENTLY
- Human issues REJECT with revision flag -> transitions to REJECTED_WITH_REVISION_ALLOWED

### REJECTED

**Description:** Human has rejected the proposed action. Action must not proceed.

**Entry:** Human issues REJECT decision.

**Exit conditions:**
- Rejection reason documented
- Agent may revise and resubmit -> new gate cycle
- No automatic retry without human acknowledgement

### REJECTED_PERMANENTLY

**Description:** Human has permanently rejected this action category. No resubmission allowed for this gate type in current context.

**Entry:** Human issues REJECT with permanent flag. Reason documented.

**Exit conditions:**
- Only a higher authority level (escalation) can override
- Action type blocked until explicit unblock

### REJECTED_WITH_REVISION_ALLOWED

**Description:** Human has rejected but allows revision and resubmission.

**Entry:** Human issues REJECT with revision flag. Revision conditions documented.

**Exit conditions:**
- Agent revises per documented conditions
- Resubmission creates new PENDING_REVIEW
- If resubmission still fails conditions -> REJECTED_PERMANENTLY

## Transitions

| From | To | Trigger |
|------|-----|---------|
| PENDING_REVIEW | REJECTED | Human REJECT decision |
| PENDING_REVIEW | REJECTED_PERMANENTLY | Human REJECT with permanent flag |
| PENDING_REVIEW | REJECTED_WITH_REVISION_ALLOWED | Human REJECT with revision flag |
| REJECTED_WITH_REVISION_ALLOWED | PENDING_REVIEW | Agent resubmits with revision |
| REJECTED_WITH_REVISION_ALLOWED | REJECTED_PERMANENTLY | Resubmission fails conditions |
