# Frozen Backlog MEDIUM-Risk Review Policy

**Task:** T1263
**Status:** release_hold = HOLD
**Scope:** 13 MEDIUM-risk frozen files

## Definition

MEDIUM-risk files are operational scripts, observation tools,
verification utilities, and documentation artifacts. They do not
contain live execution paths but may have indirect side effects.

## Inventory

### Observation Scripts
- scripts/run_shadow_observation_experiments.py
- scripts/run_observation_shift_runtime.py
- scripts/run_right_breakout_param_observation.py

### Shadow Pipeline Scripts
- scripts/run_shadow_sample_collection_pipeline.py
- scripts/run_shadow_universe_collector.py
- scripts/run_daily_shadow_scan_pipeline.py
- scripts/run_remediation_shadow_only_loop.py
- scripts/run_next_shadow_experiment_plan.py

### Verification Scripts
- scripts/verify_engineering_closeout_state.py
- tests/unit/test_verify_engineering_closeout_state_guard.py

### Operational Scripts
- scripts/live_playbook.py
- scripts/commit_recorder.sh
- scripts/replay_shadow_order_plans_as_testnet_dry.py

### Documentation
- docs/engineering_closeout_bundle.md
- docs/real_adapter_readiness.md
- docs/workflow_runtime_stack_v4.md

## Review Rules

1. Read-only access preferred - edits only with documented justification
2. Dry-run analysis required before any promotion consideration
3. Import boundary check - must not import from core/ live modules
4. Side-effect audit - network calls, file mutations, subprocess spawns

## Promotion Criteria

- Passes import boundary check
- No undocumented network calls
- No credential access patterns
- Clear operational purpose documented

## Prohibited Actions

- Running in live mode
- Committing without human approval (T1266)
