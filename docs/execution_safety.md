# Execution Safety Gate

## Scope
This project currently supports **testnet-first** execution validation.
Live trading is intentionally blocked by default.

## Testnet vs Live
- `env=testnet`:
  - Real submit is allowed only when explicit flags are enabled.
  - Default behavior is dry-run / plan-only.
- `env=live`:
  - Default is blocked.
  - Any live submit attempt must pass strict multi-condition checks.

## Why Live Is Disabled By Default
- Prevent accidental real-money orders.
- Enforce explicit operator intent.
- Enforce risk limits and symbol allowlist before any future live enablement.

## Live Enablement Conditions
`validate_execution_safety(...)` requires all conditions:
1. `execution_safety.live_trading_enabled == true`
2. `live_confirm_phrase == I_UNDERSTAND_THIS_IS_REAL_MONEY`
3. `submit_mode == live`
4. `max_notional_usdt <= execution_safety.live_max_notional_usdt`
5. `symbol in execution_safety.live_allowlist`
6. `risk_per_trade_pct <= execution_safety.live_max_risk_per_trade_pct`

If any condition fails, result is blocked with `severity=CRITICAL`.

## Suggested Config Keys
```yaml
execution_safety:
  live_trading_enabled: false
  live_confirm_phrase: I_UNDERSTAND_THIS_IS_REAL_MONEY
  live_max_notional_usdt: 0
  live_max_risk_per_trade_pct: 0
  live_allowlist: []
```

## Risk Event Logging
Blocked live attempts and execution anomalies are written to:
- `logs/risk_events.jsonl`

Key event types include:
- `LIVE_SUBMIT_BLOCKED`
- `SUBMIT_FAILED`
- `PROTECTIVE_ORDER_FAILED`
- `PROTECTIVE_ORDER_PARTIAL`
- `NAKED_POSITION_DETECTED`
- `ORPHAN_PROTECTION_DETECTED`

## Current Phase Policy
- No live submit.
- No auto real submit without explicit testnet confirmation flags.
- Continue using dry-run + testnet acceptance workflow.
