# Phase 10G-1 Future-Only Position Lifecycle Result

**Date:** 2026-06-18
**Status:** PHASE10G1_FUTURE_ONLY_POSITION_LIFECYCLE_READY

## Summary

Phase 10G-1 completed. Paper positions now use future-only lifecycle.

- Compileall: PASS
- Unit tests: 64 passed
- Offline smoke: PASS
- Real public readonly lifecycle update: PASS

## Core Changes

### 1. PaperPosition lifecycle fields

New fields:
- `opened_bar_time` — timestamp when position was opened
- `lifecycle_mode` — always `"future_only"`
- `last_checked_at` — last update time
- `last_checked_bar_time` — last bar timestamp used for update

### 2. Future-only bar filtering

```python
future_bars = [bar for bar in bars if bar.timestamp > position.opened_bar_time]
```

Bars before `opened_bar_time` are never used for TP/SL checks.

### 3. Same-intent dedup

Positions are deduplicated by `intent_id`. Running the simulator twice with the same intents does not create duplicate positions.

### 4. Closed immutability

Positions with status `TAKE_PROFIT_HIT`, `STOP_LOSS_HIT`, `TIMEOUT_EXIT`, `INVALID` are never updated.

### 5. Newly opened protection

Newly created positions are not updated in the same cycle, even if `--allow-update-newly-opened` is passed (which defaults to False).

## Smoke Results

### Real Public HTTP Lifecycle

```
Total: 21 positions
OPEN: 17
SL_HIT: 4 (from previous run, immutable)
New positions: 4
Existing positions: 17
Skipped (newly opened): 4
Skipped (no future bars): 13
Updated: 0
```

## Safety Confirmation

- Paper-only: YES
- Shadow-only: YES
- No order: YES
- No account: YES
- No testnet: YES
- No live: YES
- No secret: YES
- No .env: YES
- No real Feishu send: YES
