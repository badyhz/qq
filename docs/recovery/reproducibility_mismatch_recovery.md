# Reproducibility Mismatch Recovery

## Symptoms
- Same configuration produces different results
- Reproducibility check fails
- Deterministic seed produces non-deterministic output

## Likely Causes
- Different deterministic seed used
- Code changed between runs
- Fixture data changed between runs
- Random state leaked from environment
- Floating point non-determinism

## Commands to Inspect
```bash
# Check seeds match
grep -r "deterministic_seed" /tmp/reproducibility_run1/ /tmp/reproducibility_run2/

# Compare results
diff /tmp/reproducibility_run1/workbench_results.json /tmp/reproducibility_run2/workbench_results.json

# Check for code changes
git diff HEAD

# Check fixture integrity
md5 tests/fixtures/historical_backtest_lab/*.csv
```

## Safe Recovery Commands
```bash
# Clean previous runs
rm -rf /tmp/reproducibility_run1 /tmp/reproducibility_run2

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

# Run 2 (identical parameters)
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
diff /tmp/reproducibility_run1/workbench_results.json /tmp/reproducibility_run2/workbench_results.json && echo "REPRODUCIBLE" || echo "MISMATCH"
```

## Forbidden Recovery Commands
- Do not use different seeds between runs
- Do not modify code between runs
- Do not modify fixtures between runs
- Do not ignore mismatches

## Escalation Rule
If reproducibility fails consistently:
1. Check if code has non-deterministic elements (random, time, etc.)
2. Check if fixtures are stable
3. Run full test suite
4. If tests fail, see `docs/recovery/failed_full_suite_recovery.md`

## Final Verification
```bash
# Verify reproducibility
diff /tmp/reproducibility_run1/workbench_results.json /tmp/reproducibility_run2/workbench_results.json && echo "PASS: Reproducible" || echo "FAIL: Mismatch"
```

## Safety
release_hold = HOLD. Advisory only. Human review required.
