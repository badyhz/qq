# T13001-T13400 Offline Experiment Expansion Closeout

**Date:** 2026-05-28
**Status:** Complete
**release_hold:** HOLD

## Summary

Expanded the offline research experiment library from 20 experiments to 60 deterministic offline experiments across 20 categories.

## Changes

### Program A: Experiment Catalog Expansion
- Expanded `experiment_catalog.json` from 20 to 60 experiments
- All 20 original experiments preserved with identical IDs
- Added 40 new experiments across all 20 required categories
- Every experiment includes `category` field for classification

### Program B: Experiment Fixtures
- Created 5 example experiment fixture files in `experiments/`
- Created 10 expected manifest snapshots in `expected/`
- Expanded invalid fixtures from 6 to 12 in `invalid/`
- New invalid fixtures: `no_network_false`, `forbidden_cancel_command`, `forbidden_flatten_command`, `approval_string`, `empty_strategy_set`, `missing_artifact_set`

### Program C: Validator Hardening
- Added `no_network` safety flag check
- Added `strategy_set` non-empty validation
- Added `symbols` non-empty validation
- Added `timeframes` non-empty validation
- Added `split_mode` validation against `VALID_SPLIT_MODES`
- Added `search_budget` positive check
- Added `chunk_size` positive check
- Added `deterministic_seed` not-None check
- Added `expected_artifact_set` non-empty check
- Added `expected_review_path` non-empty check
- Added duplicate label warning
- Added category coverage check with missing category warnings
- Added forbidden token scan summary to output
- Added safety flag summary to output
- Added `output_hashes` to machine-readable output
- Added `experiment_library_version` to output

### Program D: Experiment Manifest
- Added `category_counts` to manifest
- Added `missing_categories` list
- Added `safety_flag_summary`
- Added `forbidden_token_scan` summary
- Added `expected_artifact_coverage`
- Added `recommended_review_order` (smoke first, then baseline, then others)
- Experiments sorted by ID for determinism

### Program E: Documentation
- Created `offline_research_stack_experiment_reference.md` (operator manual)
- Created `experiment_catalog_examples.md` (catalog examples)
- Created `experiment_intake_examples.md` (intake workflow)
- Created `experiment_validation_examples.md` (validation examples)
- All docs include safety flags, forbidden fields, no-auto-promotion statement, release_hold HOLD statement, external untracked warning

### Program F: Tests
- Updated `test_offline_research_experiment_library.py`: 60-experiment validation, category coverage, split mode coverage, unique IDs, no-network flag check, empty strategy set, missing artifact set
- Updated `test_offline_research_experiment_validator.py`: 12 invalid fixture tests, machine-readable output validation, category counts, duplicate label warning
- Updated `test_offline_research_experiment_catalog.py`: 60-experiment count
- Updated `test_offline_research_experiment_manifest.py`: category counts, missing categories, safety flag summary, forbidden token scan, artifact coverage, review order, sorted experiments

## Category Distribution

| Category | Count |
|---|---|
| baseline | 1 |
| strategy_specific | 4 |
| symbol_universe | 4 |
| timeframe | 4 |
| split_mode | 4 |
| search_budget | 4 |
| robustness | 4 |
| negative_control | 3 |
| bootstrap | 3 |
| regime | 3 |
| portfolio_risk | 3 |
| reproducibility | 3 |
| report_quality | 3 |
| human_review | 3 |
| smoke_test | 3 |
| stress_test | 3 |
| sparse_signal | 2 |
| noisy_fixture | 2 |
| adverse_fixture | 2 |
| comparison_analytics | 2 |

## Safety

- All experiments: `release_hold=HOLD`, `advisory_only=True`, `human_review_required=True`
- No live/testnet/runtime/planner approval strings
- No forbidden commands in allowed_commands
- No network/exchange imports in any module
- No auto-promotion capability

## Constraints Maintained

- No live/testnet/runtime/shadow files modified
- No exchange/client modules modified
- No runtime/planner modules modified
- No network calls
- No Binance/exchange dependency
- Pre-existing untracked files untouched
