# Frozen Inventory Human Review Queue

**release_hold = HOLD**
**advisory_only = True**
**human_review_required = True**

## Review Priority

### CRITICAL - Immediate Human Review Required

| File | Category | Reason |
|------|----------|--------|
| core/live_runner.py | LIVE | Runtime execution wrapper, testnet/live smoke tests |
| scripts/live_playbook.py | LIVE | Live/testnet playbook with mode selection |
| scripts/run_testnet_order_smoke.py | TESTNET | BinanceConnector, order placement path |
| scripts/run_spot_testnet_acceptance.py | TESTNET | BinanceConnector, acceptance testing |
| scripts/run_signal_testnet_trial.py | TESTNET | BinanceConnector, trial execution |
| scripts/submit_replayed_testnet_payload.py | TESTNET | BinanceFuturesTestnetClient, order submission |
| scripts/submit_approved_candidates.py | SUBMIT | Order submission with approval workflow |
| scripts/safe_flatten_testnet_symbol.py | FLATTEN | Position flattening, order cancellation |

### HIGH - Review Before Any Integration

| File | Category | Reason |
|------|----------|--------|
| scripts/run_controlled_testnet_shift.py | TESTNET | Testnet state management, order replay |
| scripts/run_replay_submit_batch.py | TESTNET | Batch order submission |
| scripts/verify_testnet_repair_scenarios.py | VERIFY | Testnet repair, order verification |
| scripts/verify_risk_release_flow.py | VERIFY | Risk release verification |
| scripts/replay_shadow_order_plans_as_testnet_dry.py | SHADOW | Shadow-to-testnet replay |

### MEDIUM - Review for Architecture Decisions

| File | Category | Reason |
|------|----------|--------|
| scripts/run_daily_shadow_scan_pipeline.py | SHADOW | Shadow pipeline orchestration |
| scripts/run_shadow_sample_collection_pipeline.py | SHADOW | Sample collection pipeline |
| scripts/run_shadow_universe_collector.py | SHADOW | Universe data collection |
| scripts/run_shadow_observation_experiments.py | SHADOW | Shadow observation experiments |
| scripts/run_next_shadow_experiment_plan.py | SHADOW | Experiment planning |
| scripts/run_remediation_shadow_only_loop.py | SHADOW | Remediation loop |
| scripts/run_observation_shift_runtime.py | OBSERVATION | Observation runtime |
| scripts/run_right_breakout_param_observation.py | OBSERVATION | Parameter observation |
| scripts/run_right_breakout_scan_dry.py | RUNTIME | Breakout scan runtime |

### LOW - Review When Convenient

| File | Category | Reason |
|------|----------|--------|
| core/evidence_recorder.py | UNKNOWN | Pure data recorder, no network |
| core/single_call_recorder.py | UNKNOWN | Pure data recorder, no network |
| research/x_aleabitoreddit_2026-05-21_2026-05-28.md | UNKNOWN | Research artifact |

## Recommended Dispositions

| Disposition | Files |
|-------------|-------|
| KEEP_FROZEN | core/live_runner.py, scripts/live_playbook.py, scripts/run_testnet_order_smoke.py, scripts/submit_replayed_testnet_payload.py, scripts/submit_approved_candidates.py, scripts/safe_flatten_testnet_symbol.py |
| NEEDS_HUMAN_REVIEW | scripts/run_controlled_testnet_shift.py, scripts/run_replay_submit_batch.py, scripts/verify_testnet_repair_scenarios.py, scripts/verify_risk_release_flow.py |
| CANDIDATE_FOR_ARCHIVE | scripts/run_daily_shadow_scan_pipeline.py, scripts/run_shadow_sample_collection_pipeline.py, scripts/run_shadow_universe_collector.py, scripts/run_shadow_observation_experiments.py, scripts/run_next_shadow_experiment_plan.py, scripts/run_remediation_shadow_only_loop.py |
| CANDIDATE_FOR_REWRITE | scripts/replay_shadow_order_plans_as_testnet_dry.py, scripts/run_observation_shift_runtime.py |
| CANDIDATE_FOR_DELETION_AFTER_BACKUP | (none recommended at this time) |
| UNKNOWN | core/evidence_recorder.py, core/single_call_recorder.py, research/x_aleabitoreddit_2026-05-21_2026-05-28.md, scripts/run_right_breakout_param_observation.py, scripts/run_right_breakout_scan_dry.py |

## Review Process

1. Human reviews each file's risk keywords and category
2. Human assigns disposition from above categories
3. For KEEP_FROZEN: no action needed, file stays as-is
4. For NEEDS_HUMAN_REVIEW: human inspects code, decides next step
5. For CANDIDATE_FOR_ARCHIVE: human approves archive location
6. For CANDIDATE_FOR_REWRITE: human specifies safety requirements
7. For CANDIDATE_FOR_DELETION_AFTER_BACKUP: human creates backup first
8. For UNKNOWN: human classifies and assigns proper disposition

## What NOT To Do

- Do not auto-promote any file
- Do not integrate any file without human approval
- Do not run any file without human approval
- Do not stage any file without explicit git add of specific path
