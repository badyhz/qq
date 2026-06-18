# Phase 10G Paper Position Simulator Result

**Date:** 2026-06-18
**Status:** PHASE10G_PAPER_POSITION_SIMULATOR_READY

## Summary

Phase 10G completed. SHADOW_READY intents → paper positions with TP/SL/PnL tracking.

- Compileall: PASS
- Unit tests: 55 passed
- Offline smoke: PASS (13 positions, 13 OPEN)
- Real public readonly update smoke: PASS (4 positions, 4 SL_HIT)

## Architecture

```
trade_intents.json        paper_position_simulator
─────────────────        ──────────────────────────
SHADOW_READY intents ──→  open_position()
                                 │
                          ┌──────┴──────┐
                          │             │
                    intent_only    kline_update
                    (OPEN)         (TP/SL check)
```

## Files

### New Modules
- `core/paper_trading/paper_position.py`
  - `PaperPosition` dataclass (shadow-only)
  - `open_position(intent)` → PaperPosition or None
  - Only accepts SHADOW_READY, shadow_only, LONG/SHORT

- `core/paper_trading/paper_position_simulator.py`
  - `simulate_intent_only(intents, date_str)` → SimulationResult
  - `simulate_with_klines(intents, bars_map, date_str)` → SimulationResult
  - `_update_position(pos, bars, timeout_bars)` — SL/TP/timeout check
  - `_calc_pnl(side, entry, exit, size)` — PnL calculation
  - `_build_summary(positions)` — per-strategy stats

### New Script
- `scripts/run_paper_position_simulator.py`
  - Default: intent_only mode
  - `--allow-public-http --update-with-klines`: real kline update

### New Tests
- `tests/unit/test_paper_position.py` (15 tests)
- `tests/unit/test_paper_position_simulator.py` (26 tests)
- `tests/unit/test_run_paper_position_simulator_script.py` (14 tests)

## Usage

```bash
# Step 1-2: Generate intents
python3 scripts/run_enabled_strategies.py --allow-public-http
python3 scripts/run_strategy_trade_intents.py

# Step 3a: Intent-only positions
python3 scripts/run_paper_position_simulator.py

# Step 3b: With kline update
python3 scripts/run_paper_position_simulator.py --allow-public-http --update-with-klines
```

## Position Status Rules

| Condition | Status |
|-----------|--------|
| intent_status != SHADOW_READY | (skipped) |
| side not LONG/SHORT | (skipped) |
| bar hits SL | STOP_LOSS_HIT |
| bar hits TP | TAKE_PROFIT_HIT |
| bar hits both SL+TP | STOP_LOSS_HIT (conservative) |
| exceeds timeout_bars | TIMEOUT_EXIT |
| no trigger | OPEN |

## PnL Formula

```
LONG:  pnl = (exit - entry) * size
SHORT: pnl = (entry - exit) * size
R:     r_multiple = pnl / (abs(entry - SL) * size)
```

## Smoke Results

### Offline (mock data)
- Positions: 13
- OPEN: 13
- SL_HIT: 0
- TP_HIT: 0

### Real Public HTTP (kline update)
- Positions: 4
- OPEN: 0
- SL_HIT: 4
- TP_HIT: 0
- Note: SHORT SL above entry triggered by current market

## Safety Confirmation

- Paper-only: YES
- Shadow-only: YES
- No order: YES
- No account: YES
- No testnet: YES
- No live: YES
- No websocket: YES
- No secret: YES
- No .env: YES
- No real Feishu send: YES
- Manual execution remains impossible: YES
