# Experiment Catalog Examples

**Status:** Offline / Advisory Only
**release_hold:** HOLD

## Valid Experiment: Baseline

```json
{
  "experiment_id": "baseline_major_5m_15m",
  "label": "Baseline Major Pairs 5m/15m",
  "description": "Baseline configuration: BTC/ETH on 5m and 15m timeframes with all four strategies.",
  "strategy_set": ["breakout", "mean_reversion", "momentum", "volatility_compression"],
  "symbols": ["BTCUSDT", "ETHUSDT"],
  "timeframes": ["5m", "15m"],
  "split_mode": "rolling",
  "search_budget": 200,
  "chunk_size": 50,
  "deterministic_seed": 424242,
  "expected_artifact_set": ["workbench_results.json", "quality_gate.json", "manifest.json"],
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
  },
  "allowed_commands": ["run_workbench", "run_quality_gate", "build_browser", "build_comparison"],
  "forbidden_commands": ["submit_order", "cancel_order", "flatten_position", "live_trading"],
  "expected_review_path": "research_human_review/",
  "notes": "Baseline experiment. Use as reference for other experiments.",
  "category": "baseline"
}
```

## Valid Experiment: Smoke Test

```json
{
  "experiment_id": "smoke_test_minimal",
  "label": "Smoke Test Minimal",
  "description": "Minimal smoke test. Single strategy, single symbol, single timeframe.",
  "strategy_set": ["breakout"],
  "symbols": ["BTCUSDT"],
  "timeframes": ["5m"],
  "split_mode": "rolling",
  "search_budget": 10,
  "chunk_size": 5,
  "deterministic_seed": 424287,
  "expected_artifact_set": ["workbench_results.json"],
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
  },
  "allowed_commands": ["run_workbench"],
  "forbidden_commands": ["submit_order", "cancel_order", "flatten_position", "live_trading"],
  "expected_review_path": "research_human_review/",
  "notes": "Minimal smoke test.",
  "category": "smoke_test"
}
```

## Valid Experiment: Stress Test

```json
{
  "experiment_id": "stress_test_many_symbols",
  "label": "Stress Test Many Symbols",
  "description": "Stress test with many symbols. Tests pipeline with wide symbol universe.",
  "strategy_set": ["breakout", "momentum"],
  "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT", "AVAXUSDT", "MATICUSDT"],
  "timeframes": ["5m"],
  "split_mode": "rolling",
  "search_budget": 400,
  "chunk_size": 100,
  "deterministic_seed": 424290,
  "expected_artifact_set": ["workbench_results.json", "quality_gate.json", "manifest.json"],
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
  },
  "allowed_commands": ["run_workbench", "run_quality_gate", "build_browser"],
  "forbidden_commands": ["submit_order", "cancel_order", "flatten_position", "live_trading"],
  "expected_review_path": "research_human_review/",
  "notes": "Many symbols stress test.",
  "category": "stress_test"
}
```
