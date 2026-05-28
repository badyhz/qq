# Experiment Validation Examples

**Status:** Offline / Advisory Only
**release_hold:** HOLD

## Running the Validator

```bash
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/offline_research_validation \
  --strict \
  --release-hold HOLD
```

## Expected Validator Output (PASS)

```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "total_experiments": 60,
  "valid_experiments": 60,
  "invalid_experiments": 0,
  "category_counts": {
    "baseline": 1,
    "strategy_specific": 4,
    "symbol_universe": 4,
    "timeframe": 4,
    "split_mode": 4,
    "search_budget": 4,
    "robustness": 4,
    "negative_control": 3,
    "bootstrap": 3,
    "regime": 3,
    "portfolio_risk": 3,
    "reproducibility": 3,
    "report_quality": 3,
    "human_review": 3,
    "smoke_test": 3,
    "stress_test": 3,
    "sparse_signal": 2,
    "noisy_fixture": 2,
    "adverse_fixture": 2,
    "comparison_analytics": 2
  },
  "release_hold": "HOLD",
  "advisory_only": true,
  "human_review_required": true,
  "generated_by": "offline_research_experiment_validator",
  "experiment_library_version": "2.0.0"
}
```

## Expected Validator Output (FAIL)

```json
{
  "valid": false,
  "errors": [
    "release_hold mismatch: expected HOLD, got RELEASE"
  ],
  "warnings": [],
  "total_experiments": 0
}
```

## Validation Error Types

| Error | Cause | Fix |
|---|---|---|
| `release_hold must be HOLD` | Safety flag wrong | Set to "HOLD" |
| `advisory_only must be True` | Safety flag wrong | Set to true |
| `human_review_required must be True` | Safety flag wrong | Set to true |
| `no_network must be True` | Safety flag wrong | Set to true |
| `forbidden_command_in_allowed: X` | Forbidden command | Remove from allowed_commands |
| `forbidden_string_detected: X` | Approval string | Remove from notes/label/description |
| `duplicate_experiment_id: X` | Duplicate ID | Use unique ID |
| `strategy_set must be non-empty` | Empty strategies | Add at least one strategy |
| `symbols must be non-empty` | Empty symbols | Add at least one symbol |
| `invalid_split_mode: X` | Bad split mode | Use rolling/anchored/walk_forward/expanding |
| `search_budget must be positive` | Zero/negative budget | Use positive number |
| `deterministic_seed must not be None` | Missing seed | Set integer seed |

## Running Tests

```bash
PYTHONPATH=. pytest -q tests/unit/test_offline_research_experiment_*.py
```
