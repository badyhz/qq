# Phase 10G-2 Legacy Paper Position Quarantine Result

**Date:** 2026-06-18
**Status:** PHASE10G2_LEGACY_POSITION_QUARANTINE_READY

## Summary

Phase 10G-2 completed. Legacy positions (pre-future-only-fix) are tagged for exclusion from performance stats.

- Compileall: PASS
- Unit tests: 28 passed
- Offline smoke: PASS (4 quarantined, 17 clean)

## What Changed

### New: `core/paper_trading/paper_position_quarantine.py`

Tags legacy positions with `quarantine_status: LEGACY_PRE_FUTURE_ONLY_FIX` and `excluded_from_performance_stats: True`.

Quarantine rules:
1. Closed status without `future_only` lifecycle
2. Missing `lifecycle_mode`
3. Missing `opened_bar_time`
4. Closed but `last_checked_bar_time <= opened_bar_time` (same-cycle update)
5. `exit_reason` contains legacy markers (`old_backtest`, `same_cycle`, `unknown`)

### New: `scripts/run_paper_position_quarantine.py`

Runner that reads `paper_positions.json`, applies quarantine, outputs:
- `_paper_positions_quarantine.json` — full tagged positions
- `_paper_positions_quarantine.md` — human-readable report
- `_paper_positions_clean_summary.json` — stats from non-excluded positions only

## Smoke Results

```
Total: 21 positions
Quarantined: 4
Clean: 17
Excluded from stats: 4
Reasons: {'closed_without_future_only_lifecycle': 4, 'missing_lifecycle_mode': 4, 'missing_opened_bar_time': 4}
```

Quarantined positions:
- PP_64348cc53289 XRPUSDT STOP_LOSS_HIT
- PP_62cba83e0b05 XRPUSDT STOP_LOSS_HIT
- PP_da60267d42c0 DOGEUSDT STOP_LOSS_HIT
- PP_d14f0ab78f52 DOGEUSDT STOP_LOSS_HIT

## Design Decisions

- **No deletion.** Legacy positions are tagged, not removed. History is preserved.
- **No recomputation.** Old PnL/status values are untouched.
- **No market data.** Quarantine is pure metadata tagging on existing records.
- **Clean summary excludes quarantined.** Performance stats only reflect future-only positions.

## Safety Confirmation

- Paper-only: YES
- Shadow-only: YES
- No order: YES
- No account: YES
- No testnet: YES
- No live: YES
- No secret: YES
- Readonly metadata only: YES
