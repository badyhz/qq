# Submit Unlock Governance Draft

**governance_mode=DRAFT_ONLY**
**submit_gate_state=LOCKED**
**testnet_submit_allowed=false**
**real_submit_allowed=false**

## Required Approvals

Minimum 3 independent human approvals: operator, reviewer, security. Each must be authenticated.

## Operator Acknowledgement

Operator must acknowledge risks, read-only constraints, and emergency procedures.

## Reviewer Acknowledgement

Reviewer must independently verify all safety controls are in place.

## Security Review

Security reviewer must verify credential vault, access control, and audit logging.

## Credential Vault Approval

Credential vault must be reviewed and approved before submit unlock.

## Adapter Implementation Review

External adapter implementation must pass code review and safety scan.

## Dry-Run Evidence

Complete dry-run evidence showing all safety controls work as designed.

## Field-Test Scope

Defined scope for field test: symbols, notional caps, duration, rollback plan.

## Max Notional Cap

Per-order notional cap must be set. Default: 100 USDT. Requires approval to increase.

## Symbol Allowlist

Only approved symbols. Default: empty. Each symbol requires individual approval.

## Kill Switch Proof

Kill switch must be tested and verified to block all submits.

## Rollback Proof

Rollback procedure must be tested and verified.

## Audit Retention Proof

Audit log retention must be verified: tamper-evident, external storage, 90-day retention.

## Submit Unlock Expiration

Submit unlock must have an expiration time. Default: 24 hours. Requires re-approval to extend.

## Submit Unlock Revocation

Any approver can revoke submit unlock immediately. Revocation logged.

## Conclusion

SUBMIT_UNLOCK_GOVERNANCE_DRAFT_READY
TESTNET_SUBMIT_NOT_ALLOWED
