# Phase 10D Strategy Library / Switchboard Result

**Date:** 2026-06-18
**Status:** PHASE10D_STRATEGY_LIBRARY_SWITCHBOARD_READY

## Summary

Phase 10D completed. Strategy library with enable/disable switchboard.

- Offline smoke: PASS
- Real public readonly smoke: PASS (21 jobs, 7 candidates, 0 errors)
- Enabled strategies: macd_rebound_watch, weak_short_watch
- Disabled strategies: breakout_pullback_watch

## Strategy Configuration

```yaml
config/strategies.yaml

strategies:
  macd_rebound_watch:
    enabled: true
    symbols: [BTCUSDT, ETHUSDT, BNBUSDT, SUIUSDT, 1000PEPEUSDT]
    timeframes: [5m, 15m, 1h]

  weak_short_watch:
    enabled: true
    symbols: [XRPUSDT, ARBUSDT, DOGEUSDT]
    timeframes: [15m, 1h]

  breakout_pullback_watch:
    enabled: false
    symbols: [BTCUSDT, ETHUSDT, SOLUSDT]
    timeframes: [15m, 1h]
```

## Real HTTP Results

### Candidates (7)
| Strategy | Symbol | TF | State | Direction |
|----------|--------|-----|-------|-----------|
| macd_rebound_watch | BNBUSDT | 1h | NEAR_TURN_UP | LONG_OBSERVE |
| weak_short_watch | XRPUSDT | 15m | SHORT_WATCH | SHORT_OBSERVE |
| weak_short_watch | XRPUSDT | 1h | SHORT_WATCH | SHORT_OBSERVE |
| weak_short_watch | ARBUSDT | 15m | SHORT_WATCH | SHORT_OBSERVE |
| weak_short_watch | ARBUSDT | 1h | SHORT_WATCH | SHORT_OBSERVE |
| weak_short_watch | DOGEUSDT | 15m | SHORT_WATCH | SHORT_OBSERVE |
| weak_short_watch | DOGEUSDT | 1h | SHORT_WATCH | SHORT_OBSERVE |

## Usage

```bash
# Offline (default)
python3 scripts/run_enabled_strategies.py

# Real public readonly HTTP
python3 scripts/run_enabled_strategies.py --allow-public-http

# Custom config
python3 scripts/run_enabled_strategies.py --config path/to/strategies.yaml

# Specific date
python3 scripts/run_enabled_strategies.py --date 2026-06-18
```

## How to Change Strategy Switch

Edit `config/strategies.yaml`:
```yaml
strategies:
  macd_rebound_watch:
    enabled: true   # change to false to disable
```

## Reports Generated

- `reports/strategies/2026-06-18_strategy_run_summary.json`
- `reports/strategies/2026-06-18_strategy_run_summary.md`
- `reports/strategies/2026-06-18_strategy_candidates.csv`
- `reports/strategies/2026-06-18_strategy_payload_input.json`

## Safety Confirmation

- Paper-only: YES
- Readonly-only: YES (public HTTP only)
- No account: YES
- No order: YES
- No testnet: YES
- No live: YES
- No websocket: YES
- No secret: YES
- No .env: YES
- No real Feishu send: YES
- No webhook storage: YES
