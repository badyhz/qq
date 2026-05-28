# Experiment Intake Examples

**Status:** Offline / Advisory Only
**release_hold:** HOLD

## Intake Checklist

Before adding a new experiment to the catalog:

1. [ ] All 16 required fields present
2. [ ] All 9 safety flags set to safe defaults
3. [ ] `release_hold` = "HOLD"
4. [ ] `advisory_only` = true
5. [ ] `human_review_required` = true
6. [ ] `no_network` = true
7. [ ] No forbidden commands in `allowed_commands`
8. [ ] No approval strings in notes/label/description
9. [ ] `strategy_set` is non-empty
10. [ ] `symbols` is non-empty
11. [ ] `timeframes` is non-empty
12. [ ] `split_mode` is one of: rolling, anchored, walk_forward, expanding
13. [ ] `search_budget` > 0
14. [ ] `chunk_size` > 0
15. [ ] `deterministic_seed` is set
16. [ ] `expected_artifact_set` is non-empty
17. [ ] `category` matches a required category

## Intake Example: New Strategy Experiment

```json
{
  "experiment_id": "my_new_strategy_5m",
  "label": "My New Strategy 5m",
  "description": "Test new strategy X on 5m timeframe.",
  "strategy_set": ["my_new_strategy"],
  "symbols": ["BTCUSDT", "ETHUSDT"],
  "timeframes": ["5m"],
  "split_mode": "rolling",
  "search_budget": 100,
  "chunk_size": 25,
  "deterministic_seed": 500001,
  "expected_artifact_set": ["workbench_results.json", "quality_gate.json"],
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
  "allowed_commands": ["run_workbench", "run_quality_gate"],
  "forbidden_commands": ["submit_order", "cancel_order", "flatten_position", "live_trading"],
  "expected_review_path": "research_human_review/",
  "notes": "New strategy isolation experiment.",
  "category": "strategy_specific"
}
```

## Common Intake Errors

### Missing safety flag
```json
{
  "safety_flags": {
    "release_hold": "HOLD",
    "advisory_only": true
  }
}
```
Error: `missing_safety_flag: human_review_required`

### Forbidden command in allowed
```json
{
  "allowed_commands": ["run_workbench", "submit_order"]
}
```
Error: `forbidden_command_in_allowed: submit_order`

### Empty strategy_set
```json
{
  "strategy_set": []
}
```
Error: `strategy_set must be non-empty list`
