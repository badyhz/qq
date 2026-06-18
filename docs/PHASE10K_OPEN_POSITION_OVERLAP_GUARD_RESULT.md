# Phase 10K Open Position Overlap Guard Result

**Date:** 2026-06-18
**Status:** PHASE10K_OPEN_POSITION_OVERLAP_GUARD_READY

## Summary

Phase 10K completed. Open position overlap guard prevents duplicate OPEN positions for same strategy+symbol+timeframe+side.

- Compileall: PASS
- Unit tests: 55 passed (37 simulator + 18 script)
- Offline smoke: PASS (overlap guard active on second run)

## What Changed

### Modified: `core/paper_trading/paper_position_simulator.py`

Added overlap guard to both `simulate_intent_only()` and `simulate_with_klines()`:

- `_build_overlap_keys(positions)` — builds `strategy_id|symbol|timeframe|side` key set from OPEN positions
- `_intent_overlap_key(intent)` — builds key from intent
- Before opening: if overlap key exists in existing OPEN set, skip intent
- Closed positions do not block (only OPEN)
- Different timeframe/side/strategy_id are not blocked

New lifecycle_stats fields:
- `positions_skipped_overlap_open` — count of skipped intents
- `skipped_overlap_intents` — list with intent metadata
- `overlap_guard_enabled` — always True
- `overlap_keys_count` — number of existing OPEN overlap keys

### Modified: `scripts/run_paper_position_simulator.py`

Added overlap guard stats to markdown and console output.

## Smoke Results

### First run (no existing positions)
```
new_positions: 13
existing_positions: 0
skipped_overlap: 0
```

### Second run (positions exist)
```
new_positions: 0
existing_positions: 58
deduped: 0
skipped_overlap: 13
overlap_guard: True
overlap_keys: 20
```

Position count stable at 58 after second run. No bloat.

## Usage

```bash
# Normal run — overlap guard is automatic
python3 scripts/run_shadow_trading_lifecycle.py --allow-public-http
```

## Safety Confirmation

- Paper-only: YES
- Shadow-only: YES
- No order: YES
- No account: YES
- No testnet: YES
- No live: YES
- No secret: YES
- No webhook stored: YES
