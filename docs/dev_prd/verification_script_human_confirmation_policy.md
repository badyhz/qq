# Verification Script Human Confirmation Policy

**Task ID:** T1287
**release_hold:** HOLD
**Status:** Active

## Policy

Human confirmation is required before any verification script is merged or promoted.

## Confirmation Steps

1. Reviewer reads the script end-to-end
2. Reviewer confirms dry-run-only proof (T1283)
3. Reviewer confirms no side effects (T1285)
4. Reviewer confirms regression tests pass (T1286)
5. Reviewer signs off with explicit approval comment

## Sign-Off Format

```
REVIEWED: verify_<name>.py
- Dry-run only: CONFIRMED
- No side effects: CONFIRMED
- Regression tests: PASS (N tests, M% coverage)
- Risk level: MEDIUM
- release_hold: HOLD
- Approved: YES / NO
```

## Escalation

- If reviewer finds issues: REJECT with specific remediation steps
- If reviewer is uncertain: ESCALATE to second reviewer
- If script touches frozen files: ESCALATE immediately

## Record Keeping

- Approval comment must be preserved in PR or review log
- No silent approvals — all confirmations must be explicit
