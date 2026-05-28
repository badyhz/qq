# Run Full Offline Research Stack

## Purpose
Run the complete offline research pipeline from workbench through human review packet.

## Prerequisites
- Python 3.10+ virtual environment
- Historical backtest fixtures in `tests/fixtures/historical_backtest_lab/`
- release_hold = HOLD
- Full test suite passing

## Commands

### Step 1: Workbench
```bash
python3 scripts/run_multi_strategy_research_workbench.py \
  --fixture-dir tests/fixtures/historical_backtest_lab \
  --output-dir /tmp/multi_strategy_research_workbench \
  --strategies breakout,mean_reversion,momentum,volatility_compression \
  --symbols BTCUSDT,ETHUSDT \
  --timeframes 5m,15m \
  --split-mode rolling \
  --search-budget 120 \
  --chunk-size 25
```

### Step 2: Quality Gate
```bash
python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --min-oos-splits 3 \
  --min-stability-score 0.60 \
  --max-parameter-fragility 0.40 \
  --max-overlap-risk 0.70 \
  --min-negative-control-margin 0.10 \
  --bootstrap-iterations 200 \
  --deterministic-seed 424242 \
  --require-negative-control \
  --require-regime-breakdown \
  --require-bootstrap \
  --require-reproducibility \
  --strict --release-hold HOLD
```

### Step 3: Artifact Browser
```bash
python3 scripts/build_research_artifact_browser.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --output-dir /tmp/research_artifact_browser \
  --strict --release-hold HOLD
```

### Step 4: Comparison Analytics
```bash
python3 scripts/build_research_comparison_analytics.py \
  --bundle baseline=/tmp/research_artifact_browser \
  --bundle candidate=/tmp/research_artifact_browser \
  --output-dir /tmp/research_comparison_analytics \
  --strict --release-hold HOLD
```

### Step 5: Human Review Packet
```bash
python3 scripts/build_research_human_review_packet.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --artifact-browser-dir /tmp/research_artifact_browser \
  --comparison-dir /tmp/research_comparison_analytics \
  --output-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

### Step 6: Validate Review Packet
```bash
python3 scripts/validate_research_human_review_packet.py \
  --review-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

## Expected Outputs
- `/tmp/multi_strategy_research_workbench/` — workbench results
- `/tmp/multi_strategy_research_quality_gate/` — quality gate results
- `/tmp/research_artifact_browser/` — artifact browser
- `/tmp/research_comparison_analytics/` — comparison analytics
- `/tmp/research_human_review_packet/` — review packet

## PASS Criteria
- All 6 stages complete without error
- Quality gate verdict = PASS
- Review packet validation = PASS
- release_hold = HOLD throughout

## FAIL Criteria
- Any stage returns non-zero exit code
- Quality gate verdict != PASS
- Review packet validation fails
- release_hold changes from HOLD

## Safety Notes
- All stages use --strict --release-hold HOLD
- Output is advisory only
- Human review required before any promotion
- No live/testnet/runtime/planner integration

## Forbidden Actions
- Do not change --release-hold from HOLD
- Do not skip quality gate
- Do not skip review packet validation
- Do not auto-promote results

## Recovery Path
If any stage fails:
1. Check error output
2. See relevant recovery doc in `docs/recovery/`
3. Fix issue
4. Re-run failed stage
5. Continue pipeline from that point
