# T13401-T13600: Frozen Inventory Next Actions

## Current State

- 25 pre-existing untracked live/testnet/shadow/runtime files inventoried
- All files remain frozen (untracked, unstaged, unmodified)
- release_hold = HOLD
- System remains offline / advisory-only

## Immediate Next Actions

### 1. Human Review Queue

Priority order for human review:

**CRITICAL (8 files)**:
- core/live_runner.py
- scripts/live_playbook.py
- scripts/run_testnet_order_smoke.py
- scripts/run_spot_testnet_acceptance.py
- scripts/run_signal_testnet_trial.py
- scripts/submit_replayed_testnet_payload.py
- scripts/submit_approved_candidates.py
- scripts/safe_flatten_testnet_symbol.py

**HIGH (5 files)**:
- scripts/run_controlled_testnet_shift.py
- scripts/run_replay_submit_batch.py
- scripts/verify_testnet_repair_scenarios.py
- scripts/verify_risk_release_flow.py
- scripts/replay_shadow_order_plans_as_testnet_dry.py

**MEDIUM (9 files)**:
- scripts/run_daily_shadow_scan_pipeline.py
- scripts/run_shadow_sample_collection_pipeline.py
- scripts/run_shadow_universe_collector.py
- scripts/run_shadow_observation_experiments.py
- scripts/run_next_shadow_experiment_plan.py
- scripts/run_remediation_shadow_only_loop.py
- scripts/run_observation_shift_runtime.py
- scripts/run_right_breakout_param_observation.py
- scripts/run_right_breakout_scan_dry.py

**LOW (3 files)**:
- core/evidence_recorder.py
- core/single_call_recorder.py
- research/x_aleabitoreddit_2026-05-21_2026-05-28.md

### 2. Disposition Assignment

Human assigns each file to one of:
- KEEP_FROZEN
- NEEDS_HUMAN_REVIEW
- CANDIDATE_FOR_ARCHIVE
- CANDIDATE_FOR_REWRITE
- CANDIDATE_FOR_DELETION_AFTER_BACKUP
- UNKNOWN

### 3. Post-Approval Actions

After human approval:
1. Re-run inventory scanner to confirm state
2. Archive approved files if needed
3. Rewrite files with safety constraints if needed
4. Update disposition documentation
5. Confirm release_hold status

## What NOT To Do

1. Do not execute any frozen file
2. Do not import any frozen module
3. Do not stage any frozen file
4. Do not connect to Binance/network
5. Do not place/cancel/flatten orders
6. Do not auto-promote any file
7. Do not use `git add .`

## Exact Future Prompt for Human-Approved Review Phase

```
Human has approved review of frozen inventory at docs/frozen_inventory/.
Release hold status: [HOLD/RELEASED]
Approved files: [list of files]
Approved dispositions: [KEEP_FROZEN/NEEDS_HUMAN_REVIEW/CANDIDATE_FOR_ARCHIVE/etc.]
Safety constraints: [specific constraints per file]
Next action: [archive/rewrite/delete/integrate with constraints]
```

## Reminder

This is inventory only. No activation. No promotion. No execution.
Live/testnet/shadow files remain frozen external state.
