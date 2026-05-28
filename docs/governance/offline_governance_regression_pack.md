# Offline Governance Regression Pack

## Purpose

One CLI that runs key offline governance checks in sequence.

## Checks

1. validate_offline_research_experiment_library — Experiment library tests
2. validate_offline_research_stack_docs — Documentation and governance validation
3. build_frozen_inventory_report — Build frozen inventory report
4. build_frozen_inventory_decision_matrix — Build decision matrix
5. build_frozen_inventory_archive_plan — Build archive plan
6. build_offline_research_result_catalog — Build result catalog

## Safety

- No shell=True
- No network commands
- No frozen file execution
- No live/testnet/runtime
- subprocess only for local Python scripts

## Output Fields

- check name
- command
- status PASS/FAIL/SKIPPED
- output path
- duration
- safety flags
- release_hold
- advisory_only
- errors
- warnings
- final verdict

## CLI

```bash
python3 scripts/run_offline_governance_regression_pack.py \
    --output-dir /tmp/offline_governance_regression_pack \
    --strict \
    --release-hold HOLD
```

## Outputs

- regression_pack.json
- regression_pack.md
- regression_pack_manifest.json
