# Threat Model and Security Review Checklist

**Status: THREAT_MODEL_SECURITY_REVIEW_READY**
**Submit: TESTNET_SUBMIT_NOT_ALLOWED**

| Threat | Category | Status |
|--------|----------|--------|
| API secret leaked through logs, errors, or debug output | credential_leakage | DESIGNED |
| API key granted more permissions than needed | permission_overreach | DESIGNED |
| Withdraw permission accidentally enabled | withdraw_permission_exposure | DESIGNED |
| Signed request replayed by attacker | replay_attack | DESIGNED |
| Order submitted multiple times | duplicate_submit | DESIGNED |
| Order submitted based on stale signal | stale_signal_submit | DESIGNED |
| Request times out, unknown state | network_timeout | DESIGNED |
| Server returns partial response | partial_response | DESIGNED |
| Cancel request fails, order remains open | cancel_failure | DESIGNED |
| Local state differs from exchange state | reconciliation_mismatch | DESIGNED |
| Audit log tampered or deleted | audit_tampering | DESIGNED |
| Operator makes mistake (wrong symbol, wrong size) | operator_error | DESIGNED |
| Fake approval submitted | approval_spoofing | DESIGNED |
| Kill switch fails to block submit | kill_switch_failure | DESIGNED |
| Rollback fails or corrupts state | rollback_failure | DESIGNED |

## Conclusion

THREAT_MODEL_SECURITY_REVIEW_READY
TESTNET_SUBMIT_NOT_ALLOWED
