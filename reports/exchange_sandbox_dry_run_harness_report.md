# Exchange Sandbox Dry-Run Harness Report

## Steps

| Step | Status | Detail |
|------|--------|--------|
| load_profile | SIMULATED | profile=binance_testnet, key=REDACTED |
| validate_permissions | PASS | stub permissions: SPOT_READ, SPOT_TRADE |
| build_order_request | SIMULATED | BTCUSDT BUY 0.001 LIMIT 50000 |
| simulate_signing | SIMULATED | fake_signature=***REDACTED*** |
| simulate_submit | SIMULATED | SIM_ORD_001 status=SIMULATED_NEW |
| simulate_cancel | SIMULATED | SIM_ORD_001 status=SIMULATED_CANCELLED |
| simulate_balance | SIMULATED | USDT=10000 BTC=0.5 |
| simulate_positions | SIMULATED | no positions |

## Safety

- no_network: True
- no_real_key: True
- no_submit: True

## Conclusion

EXCHANGE_SANDBOX_DRY_RUN_HARNESS_PASS
