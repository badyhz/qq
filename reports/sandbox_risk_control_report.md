# Sandbox Risk Control Report

| Check | Passed | Detail |
|-------|--------|--------|
| max_notional | True | notional=50.00, max=1000.0 |
| symbol_allowed | True | symbol=BTCUSDT |
| symbol_not_blocked | True | symbol=BTCUSDT |
| daily_order_count | True | count=5, max=50 |
| price_sanity | True | deviation=0.00%, max=5.0% |
| duplicate_intent | True | intent_id=INT_TEST, already_seen=False |
| stale_signal | True | signal_timestamp=2026-06-14T00:00:00Z, max_age=3600.0s |
| approval_required | True | approval_status=DENIED |
| kill_switch | True | kill_switch_blocking=True |

## Conclusion

ALL_CHECKS_PASSED: True
