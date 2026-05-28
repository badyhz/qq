# Frozen Testnet / Runtime Inventory

## Overview

This document catalogs all pre-existing untracked live/testnet/shadow/runtime-related files found in the working tree as of T13600. These files have been accumulating as untracked artifacts and represent frozen external state.

**release_hold = HOLD**
**advisory_only = True**
**human_review_required = True**

No file listed here has been activated, promoted, staged, imported, or executed as part of this inventory.

## Inventory Summary

Total files inventoried: 25

| Category    | Count |
|-------------|-------|
| LIVE        | 3     |
| TESTNET     | 10    |
| SHADOW      | 7     |
| OBSERVATION | 2     |
| VERIFY      | 2     |
| RUNTIME     | 1     |
| UNKNOWN     | 1     |

## File List

### core/

| File | Category | Risk Keywords |
|------|----------|---------------|
| core/live_runner.py | LIVE | live, testnet, preflight, execution, order |
| core/evidence_recorder.py | UNKNOWN | (none - pure data recorder) |
| core/single_call_recorder.py | UNKNOWN | (none - pure data recorder) |

### scripts/ - LIVE

| File | Category | Risk Keywords |
|------|----------|---------------|
| scripts/live_playbook.py | LIVE | live, testnet, execution, order, exchange |

### scripts/ - TESTNET

| File | Category | Risk Keywords |
|------|----------|---------------|
| scripts/run_testnet_order_smoke.py | TESTNET | testnet, order, binance, api_key, secret, requests |
| scripts/run_spot_testnet_acceptance.py | TESTNET | testnet, binance, order, exchange |
| scripts/run_signal_testnet_trial.py | TESTNET | testnet, binance, order, exchange |
| scripts/run_controlled_testnet_shift.py | TESTNET | testnet, submit, order, cancel, flatten |
| scripts/run_replay_submit_batch.py | TESTNET | testnet, submit, order |
| scripts/submit_replayed_testnet_payload.py | TESTNET | testnet, submit, order, binance, fapi, api_key, secret |
| scripts/submit_approved_candidates.py | SUBMIT | submit, approve, flatten, cancel, order |
| scripts/safe_flatten_testnet_symbol.py | FLATTEN | testnet, flatten, cancel, binance |

### scripts/ - SHADOW

| File | Category | Risk Keywords |
|------|----------|---------------|
| scripts/run_daily_shadow_scan_pipeline.py | SHADOW | shadow, observation, testnet, submit |
| scripts/run_next_shadow_experiment_plan.py | SHADOW | shadow, observation |
| scripts/run_shadow_observation_experiments.py | SHADOW | shadow, observation, runtime |
| scripts/run_shadow_sample_collection_pipeline.py | SHADOW | shadow, observation |
| scripts/run_shadow_universe_collector.py | SHADOW | shadow |
| scripts/run_remediation_shadow_only_loop.py | SHADOW | shadow, runtime |
| scripts/replay_shadow_order_plans_as_testnet_dry.py | SHADOW | shadow, testnet, order, binance |

### scripts/ - OBSERVATION / RUNTIME

| File | Category | Risk Keywords |
|------|----------|---------------|
| scripts/run_observation_shift_runtime.py | OBSERVATION | observation, runtime, testnet |
| scripts/run_right_breakout_param_observation.py | OBSERVATION | observation, runtime, binance |
| scripts/run_right_breakout_scan_dry.py | RUNTIME | runtime, binance, order |

### scripts/ - VERIFY

| File | Category | Risk Keywords |
|------|----------|---------------|
| scripts/verify_risk_release_flow.py | VERIFY | verify, release, submit, testnet |
| scripts/verify_testnet_repair_scenarios.py | VERIFY | verify, testnet, submit, order, binance |

### research/

| File | Category | Risk Keywords |
|------|----------|---------------|
| research/x_aleabitoreddit_2026-05-21_2026-05-28.md | UNKNOWN | (research artifact) |

## Safety Boundary

- No execution. No import. No staging.
- release_hold = HOLD
- Advisory only. Human review required.
- All files remain frozen external state.
