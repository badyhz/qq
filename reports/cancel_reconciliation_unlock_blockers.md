# Cancel and Reconciliation Unlock Blockers

## Cancel Gate

**Status: CANCEL_GATE_REMAINS_LOCKED**

| Blocker | Status |
|---------|--------|
| Real cancel adapter missing | BLOCKING |
| Cancel idempotency not field-tested | REQUIRES_FIELD_TEST |
| Terminal order handling not field-tested | REQUIRES_FIELD_TEST |
| Unknown order handling not field-tested | REQUIRES_FIELD_TEST |
| Audit trail storage missing | BLOCKING |
| Operator emergency cancel flow missing | REQUIRES_FIELD_TEST |

## Reconciliation Gate

**Status: RECONCILIATION_GATE_REMAINS_LOCKED**

| Blocker | Status |
|---------|--------|
| Real balance fetch missing | BLOCKING |
| Real position fetch missing | BLOCKING |
| Snapshot staleness threshold not field-tested | REQUIRES_FIELD_TEST |
| Mismatch handling not field-tested | REQUIRES_FIELD_TEST |
| Manual override policy missing | REQUIRES_HUMAN_APPROVAL |
| Audit chain external storage missing | BLOCKING |

## Conclusion

CANCEL_GATE_REMAINS_LOCKED
RECONCILIATION_GATE_REMAINS_LOCKED
TESTNET_SUBMIT_NOT_ALLOWED
