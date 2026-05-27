# Verification Script Blocked State Policy

**Task ID:** T1289
**release_hold:** HOLD
**Status:** Active

## Policy

A verification script enters BLOCKED state when any promotion checklist item fails.

## Blocking Triggers

1. High-risk import detected without mock
2. Dry-run-only proof missing or failed
3. Unmocked external dependency found
4. Side effect detected in pre/post diff
5. Regression tests missing or failing
6. Human reviewer rejected with remediation notes
7. Script touches frozen or blocked files

## Blocked State Behavior

- Script MUST NOT be merged
- Script MUST NOT be promoted
- release_hold remains HOLD
- Blocker must be documented with specific file/line reference

## Remediation Workflow

1. Identify blocker from checklist
2. Fix the specific issue
3. Re-run all checks from T1282-T1287
4. Request re-review from human
5. Clear blocker only when all checks pass

## Escalation

- If blocker persists after 2 remediation attempts: ESCALATE
- If blocker involves frozen files: ESCALATE immediately
- If blocker is ambiguous: ESCALATE to second reviewer
