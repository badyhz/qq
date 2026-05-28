# Rerun Reproducibility Check

## Purpose
Verify deterministic reproducibility by running the same configuration twice and comparing results.

## Prerequisites
- Offline pipeline completed at least once
- Same deterministic seed available
- release_hold = HOLD

## Commands
```bash
# Run 1
python3 scripts/run_multi_strategy_research_workbench.py \
  --fixture-dir tests/fixtures/historical_backtest_lab \
  --output-dir /tmp/reproducibility_run1 \
  --strategies breakout,momentum \
  --symbols BTCUSDT,ETHUSDT \
  --timeframes 5m \
  --split-mode rolling \
  --search-budget 100 \
  --chunk-size 25

# Run 2 (same parameters)
python3 scripts/run_multi_strategy_research_workbench.py \
  --fixture-dir tests/fixtures/historical_backtest_lab \
  --output-dir /tmp/reproducibility_run2 \
  --strategies breakout,momentum \
  --symbols BTCUSDT,ETHUSDT \
  --timeframes 5m \
  --split-mode rolling \
  --search-budget 100 \
  --chunk-size 25

# Compare
diff /tmp/reproducibility_run1/workbench_results.json /tmp/reproducibility_run2/workbench_results.json
```

## Expected Outputs
- Both runs produce identical results
- `diff` shows no differences

## PASS Criteria
- Both runs complete successfully
- Results are identical (diff empty)
- Same deterministic seed used

## FAIL Criteria
- Results differ between runs
- Different seeds used
- Code or fixtures changed between runs

## Safety Notes
- Offline only
- Advisory only
- release_hold = HOLD

## Forbidden Actions
- Do not change parameters between runs
- Do not modify fixtures between runs
- Do not change code between runs

## Recovery Path
See `docs/recovery/reproducibility_mismatch_recovery.md`
