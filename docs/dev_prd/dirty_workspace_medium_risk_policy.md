# Dirty Workspace MEDIUM Risk Policy

## Purpose

Define rules for files classified as MEDIUM risk. These files require review but are not frozen.

## Rules

### Review Required

Every MEDIUM-risk file must undergo a review before commit. The review must confirm:
- Content matches stated purpose
- No embedded secrets or credentials
- No unintended side effects
- No frozen-boundary violations

### May Commit After Human Approval

MEDIUM-risk files may be committed after human approval. The approval must be explicit — silence or absence of objection is not approval.

### Must Not Bypass Safety Checks

MEDIUM-risk files must pass all safety checks before commit:
- Classification verified
- Diff reviewed
- No HIGH-risk dependencies introduced
- No duplicate file conflicts

## Typical Categories

MEDIUM risk applies to:
- **A (Route):** Routing logic that dispatches to other modules
- **E (Scripts):** Operational scripts that may interact with external systems

## Escalation

If a MEDIUM-risk file review reveals concerns that elevate its risk profile, it must be reclassified as HIGH and subject to the HIGH-risk policy.
