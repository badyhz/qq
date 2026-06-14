# Field-Test Acceptance Criteria

**field_test_mode=CRITERIA_ONLY**
**field_test_executed=false**
**submit_allowed=false**

## Dry-Run Parity Before Field Test

All dry-run tests must pass before field test begins.

## Credential Vault Approved

Credential vault must be reviewed and approved.

## Request Signing Reviewed

Request signing implementation must be reviewed.

## Network Transport Reviewed

Network transport implementation must be reviewed.

## Submit Gate Temporary Unlock Approval

Explicit approval for temporary submit unlock during field test.

## Cancel Gate Temporary Unlock Approval

Explicit approval for temporary cancel unlock during field test.

## Reconciliation Gate Temporary Unlock Approval

Explicit approval for temporary reconciliation unlock during field test.

## Symbol Allowlist

Only approved symbols allowed during field test.

## Notional Cap

Per-order notional cap set and enforced.

## Daily Order Cap

Daily order cap set and enforced.

## Manual Operator Present

Operator must be present during entire field test.

## Kill Switch Armed

Kill switch must be armed and tested.

## Audit Log External Backup

Audit log backed up to external storage before field test.

## Rollback Rehearsal

Rollback procedure rehearsed before field test.

## Post-Test Review

Post-test review required before next phase.

## Conclusion

FIELD_TEST_ACCEPTANCE_CRITERIA_READY
TESTNET_SUBMIT_NOT_ALLOWED
