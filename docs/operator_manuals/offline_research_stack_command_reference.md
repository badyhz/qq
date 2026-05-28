# Offline Research Stack Command Reference

## Validation Commands

### Validate Experiment Library
```bash
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/offline_research_experiment_library_validation \
  --strict --release-hold HOLD
```
Output: `experiment_library_validation.json`, `experiment_library_manifest.json`

### Validate Docs Governance
```bash
python3 scripts/validate_offline_research_stack_docs.py \
  --docs-root docs \
  --output-dir /tmp/offline_research_governance_validation \
  --strict --release-hold HOLD
```
Output: `governance_validation.json`, `governance_validation.md`, `governance_manifest.json`

### Build Operator Bundle
```bash
python3 scripts/build_offline_research_operator_bundle.py \
  --docs-root docs \
  --experiment-catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/offline_research_operator_bundle \
  --strict --release-hold HOLD
```
Output: 8 artifacts (index, manifest, MD, HTML, cheatsheets, summary)

## Pipeline Commands

### Workbench
```bash
python3 scripts/run_multi_strategy_research_workbench.py \
  --fixture-dir tests/fixtures/historical_backtest_lab \
  --output-dir /tmp/multi_strategy_research_workbench \
  --strategies <strategy_list> \
  --symbols <symbol_list> \
  --timeframes <timeframe_list> \
  --split-mode <rolling|anchored> \
  --search-budget <int> \
  --chunk-size <int>
```

### Quality Gate
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

### Artifact Browser
```bash
python3 scripts/build_research_artifact_browser.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --output-dir /tmp/research_artifact_browser \
  --strict --release-hold HOLD
```

### Comparison Analytics
```bash
python3 scripts/build_research_comparison_analytics.py \
  --bundle <name>=<path> \
  --bundle <name>=<path> \
  --output-dir /tmp/research_comparison_analytics \
  --strict --release-hold HOLD
```

### Human Review Packet
```bash
python3 scripts/build_research_human_review_packet.py \
  --quality-dir <path> \
  --artifact-browser-dir <path> \
  --comparison-dir <path> \
  --output-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

### Validate Review Packet
```bash
python3 scripts/validate_research_human_review_packet.py \
  --review-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

## Test Commands

### Full Test Suite
```bash
PYTHONPATH=. .venv/bin/pytest -q
```

### Targeted Tests
```bash
# Experiment library
PYTHONPATH=. .venv/bin/pytest tests/unit/test_offline_research_experiment_*.py -q

# Governance
PYTHONPATH=. .venv/bin/pytest tests/unit/test_offline_research_governance*.py -q

# Operator docs
PYTHONPATH=. .venv/bin/pytest tests/unit/test_offline_research_operator_*.py -q

# Runbooks
PYTHONPATH=. .venv/bin/pytest tests/unit/test_offline_research_runbooks*.py -q

# Checklists
PYTHONPATH=. .venv/bin/pytest tests/unit/test_offline_research_checklists*.py -q

# Recovery docs
PYTHONPATH=. .venv/bin/pytest tests/unit/test_offline_research_recovery_docs*.py -q
```

## Safety

All commands require `--release-hold HOLD`. Never change this value without explicit human approval.
