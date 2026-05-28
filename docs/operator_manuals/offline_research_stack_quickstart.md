# Offline Research Stack Quickstart

## Prerequisites

- Python 3.10+
- Virtual environment set up
- Historical backtest fixtures in `tests/fixtures/historical_backtest_lab/`
- release_hold = HOLD

## Quick Start Steps

### 1. Validate Environment
```bash
python3 scripts/validate_offline_research_stack_docs.py \
  --docs-root docs \
  --output-dir /tmp/offline_research_governance_validation \
  --strict --release-hold HOLD
```

### 2. Validate Experiment Library
```bash
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/offline_research_experiment_library_validation \
  --strict --release-hold HOLD
```

### 3. Run Offline Pipeline
```bash
# Workbench
python3 scripts/run_multi_strategy_research_workbench.py \
  --fixture-dir tests/fixtures/historical_backtest_lab \
  --output-dir /tmp/multi_strategy_research_workbench \
  --strategies breakout,mean_reversion,momentum,volatility_compression \
  --symbols BTCUSDT,ETHUSDT --timeframes 5m,15m \
  --split-mode rolling --search-budget 120 --chunk-size 25

# Quality Gate
python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --deterministic-seed 424242 --strict --release-hold HOLD

# Artifact Browser
python3 scripts/build_research_artifact_browser.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --output-dir /tmp/research_artifact_browser \
  --strict --release-hold HOLD

# Comparison
python3 scripts/build_research_comparison_analytics.py \
  --bundle baseline=/tmp/research_artifact_browser \
  --bundle candidate=/tmp/research_artifact_browser \
  --output-dir /tmp/research_comparison_analytics \
  --strict --release-hold HOLD

# Review Packet
python3 scripts/build_research_human_review_packet.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --artifact-browser-dir /tmp/research_artifact_browser \
  --comparison-dir /tmp/research_comparison_analytics \
  --output-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

### 4. Run Tests
```bash
PYTHONPATH=. .venv/bin/pytest -q
```

### 5. Build Operator Bundle
```bash
python3 scripts/build_offline_research_operator_bundle.py \
  --docs-root docs \
  --experiment-catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/offline_research_operator_bundle \
  --strict --release-hold HOLD
```

## Safety Reminder

- release_hold = HOLD
- Advisory only
- No live/testnet/runtime/planner
- No auto-promotion
- Human review required
