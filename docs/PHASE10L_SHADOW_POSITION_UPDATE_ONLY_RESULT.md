# Phase 10L: Shadow Position Update-Only Pipeline

## Summary

Added update-only pipeline for managing existing OPEN paper positions without scanning new strategies or generating new TradeIntents.

## Files Changed

### Core
- `core/paper_trading/paper_position_simulator.py` — added `simulate_existing_positions_update_only()` function
  - Never creates new positions
  - Updates only existing OPEN positions with klines
  - Closed positions stay closed (immutability)
  - Missing bars → skipped safely

### Scripts
- `scripts/run_paper_position_simulator.py` — added `--update-existing-only` flag
  - When set: skips intent loading, only updates existing positions
  - Mode: `update_existing_only (future_only)`
- `scripts/run_shadow_position_update_only.py` — new 4-step pipeline
  1. `run_paper_position_simulator --update-existing-only`
  2. `run_paper_position_quarantine`
  3. `run_paper_performance_scorecard`
  4. `run_sample_collection_gate`
  - Does NOT call `run_enabled_strategies` or `run_strategy_trade_intents`
  - Registers each run in registry
  - Outputs `_shadow_position_update_result.json/md`

### Tests
- `tests/unit/test_paper_position_simulator.py` — +9 TestUpdateOnly tests
- `tests/unit/test_run_paper_position_simulator_script.py` — +1 test (`test_has_update_existing_only`)
- `tests/unit/test_run_shadow_position_update_only_script.py` — new, 18 tests

## Safety

- Paper-only: YES
- Shadow-only: YES
- No new positions: YES (enforced by `simulate_existing_positions_update_only`)
- No strategy scan: YES (pipeline skips strategy/intent scripts)
- No trade intent generation: YES
- No order: YES
- No account: YES
- No testnet/live: YES
- No secret: YES
- No env reads: YES
- No shell=True: YES
- No websocket: YES

## Update-Only Pipeline Flow

```
Existing OPEN positions
    ↓
run_paper_position_simulator --update-existing-only
    ↓ (update with klines: TP/SL/timeout check)
run_paper_position_quarantine
    ↓ (tag legacy, compute clean summary)
run_paper_performance_scorecard
    ↓ (compute metrics, strategy scorecards)
run_sample_collection_gate
    ↓ (evaluate testnet readiness)
Result: _shadow_position_update_result.json/md
```

## Lifecycle Stats (update-only mode)

- `new_positions_count`: always 0
- `existing_positions_count`: count of input positions
- `positions_updated_count`: positions that received kline update
- `positions_skipped_no_future_bars`: positions with no bars after opened_bar_time
- `positions_skipped_closed`: closed positions (immutability)
- `positions_skipped_missing_bars`: positions without matching bar data
- `update_only`: True

## Commit Plan

```
git add core/paper_trading/paper_position_simulator.py tests/unit/test_paper_position_simulator.py
git commit -m "Add update-only paper position simulation"

git add scripts/run_paper_position_simulator.py tests/unit/test_run_paper_position_simulator_script.py
git commit -m "Add update-only mode to paper position runner"

git add scripts/run_shadow_position_update_only.py tests/unit/test_run_shadow_position_update_only_script.py
git commit -m "Add shadow position update-only pipeline"

git add docs/PHASE10L_SHADOW_POSITION_UPDATE_ONLY_RESULT.md
git commit -m "Document shadow position update-only pipeline"
```
