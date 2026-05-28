# Offline Research Experiment Library Reference

**Version:** 2.0.0
**Status:** Offline / Advisory Only
**release_hold:** HOLD

## Overview

The offline research experiment library contains 60 deterministic experiments across 20 categories. All experiments are offline, advisory-only, and require human review before any promotion decisions.

**No experiment in this library authorizes live trading, testnet submission, runtime activation, or planner integration.**

## How to Choose an Experiment

1. **Start with smoke tests** (`smoke_test` category) to validate pipeline setup.
2. **Run baseline** (`baseline` category) to establish reference performance.
3. **Explore strategy-specific** experiments to understand individual strategy behavior.
4. **Test robustness** across split modes, timeframes, and symbol universes.
5. **Run negative controls** to verify strategies do not overfit to noise.
6. **Use stress tests** to validate pipeline under load.

## Category Map

| Category | Count | Description |
|---|---|---|
| baseline | 1 | Reference configuration for all strategies |
| strategy_specific | 4 | Individual strategy isolation tests |
| symbol_universe | 4 | Symbol diversity experiments |
| timeframe | 4 | Timeframe variation tests |
| split_mode | 4 | Split mode comparison (rolling, anchored, walk_forward, expanding) |
| search_budget | 4 | Budget variation from ultra-low to very-high |
| robustness | 4 | Parameter fragility and seed independence |
| negative_control | 3 | Overfit resistance validation |
| bootstrap | 3 | Confidence interval estimation |
| regime | 3 | Market regime breakdown analysis |
| portfolio_risk | 3 | Portfolio overlap and concentration |
| reproducibility | 3 | Bit-exact reproducibility verification |
| report_quality | 3 | Output report completeness validation |
| human_review | 3 | Review packet generation and validation |
| smoke_test | 3 | Fast pipeline validation |
| stress_test | 3 | Pipeline load testing |
| sparse_signal | 2 | Low-frequency signal behavior |
| noisy_fixture | 2 | Data noise resilience |
| adverse_fixture | 2 | Bear market and flash crash scenarios |
| comparison_analytics | 2 | Cross-strategy and cross-symbol comparison |

## Required Safety Flags

Every experiment must include all of:

```
release_hold: HOLD
advisory_only: true
human_review_required: true
no_live: true
no_submit: true
no_exchange: true
no_network: true
no_runtime_integration: true
no_planner_integration: true
```

## Forbidden Fields

No experiment may contain:
- `APPROVE_LIVE`, `APPROVE_TESTNET`, `APPROVE_RUNTIME`, `APPROVE_PLANNER`
- `auto_promote`, `live_trading`, `testnet_submit`
- `submit_order`, `cancel_order`, `flatten_position`, `place_order` in allowed_commands
- `runtime_start`, `planner_run`, `exchange_connect`, `binance_client` in allowed_commands

## How to Validate the Catalog

```bash
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/offline_research_experiment_validation \
  --strict \
  --release-hold HOLD
```

## How to Add a New Offline Experiment Safely

1. Create experiment definition with all required fields.
2. Set all safety flags to safe defaults (see above).
3. Add `category` field matching one of the 20 required categories.
4. Verify `deterministic_seed` is set to a unique integer.
5. Run validator in strict mode.
6. Run test suite to confirm no regressions.
7. Update catalog JSON file.
8. Commit with explicit `git add` of catalog file only.

## Review Workflow Path

1. Run experiment offline via workbench.
2. Validate output with quality gate.
3. Build review packet.
4. Human reviews packet.
5. Human decides: no promotion, further research, or advisory recommendation.
6. **No automatic promotion is possible.**

## Valid Experiment Example

```json
{
  "experiment_id": "baseline_major_5m_15m",
  "label": "Baseline Major Pairs 5m/15m",
  "strategy_set": ["breakout", "mean_reversion", "momentum", "volatility_compression"],
  "symbols": ["BTCUSDT", "ETHUSDT"],
  "timeframes": ["5m", "15m"],
  "split_mode": "rolling",
  "search_budget": 200,
  "chunk_size": 50,
  "deterministic_seed": 424242,
  "safety_flags": {
    "release_hold": "HOLD",
    "advisory_only": true,
    "human_review_required": true,
    "no_live": true,
    "no_submit": true,
    "no_exchange": true,
    "no_network": true,
    "no_runtime_integration": true,
    "no_planner_integration": true
  }
}
```

## Invalid Experiment Examples

**Missing release_hold:**
```json
{ "safety_flags": { "advisory_only": true } }
```

**Forbidden command in allowed:**
```json
{ "allowed_commands": ["run_workbench", "submit_order"] }
```

**Approval string in notes:**
```json
{ "notes": "This experiment APPROVE_LIVE for production." }
```

## No Auto-Promotion Statement

This library is strictly offline and advisory. No experiment, regardless of results, can automatically promote to live, testnet, or runtime. All promotion decisions require explicit human approval through the governance review process.

## release_hold HOLD Statement

The `release_hold` flag is permanently set to `HOLD`. This is a safety mechanism that prevents any automated system from progressing experiments beyond the offline/advisory stage.

## External Untracked Warning

The repository may contain pre-existing untracked files for live/testnet/shadow operations. These files are external state and must not be staged, imported, executed, or modified as part of offline experiment work.
