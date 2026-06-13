# Frozen File Cleanup Decision Matrix

**Total decisions:** 23
**release_hold:** HOLD
**simulation_only:** true for all items

## Safety Boundary

- would_copy: **false** for all items
- would_move: **false** for all items
- would_delete: **false** for all items
- would_modify: **false** for all items
- simulation_only: **true** for all items
- human_approval_required: **true** for all items
- no_touch_required: **true** for all items
- advisory_only: **true** for all items

## Decision Summary

- **RETAIN_FROZEN:** 23

## Classification Summary

- **RETAIN:** 23

## Decision Items

### core/live_runner.py

- **decision_id:** decision_core__live_runner_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** high_risk_retain_until_evidence_and_approval
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/live_playbook.py

- **decision_id:** decision_scripts__live_playbook_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** high_risk_retain_until_evidence_and_approval
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/submit_approved_candidates.py

- **decision_id:** decision_scripts__submit_approved_candidates_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** high_risk_retain_until_evidence_and_approval
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_testnet_order_smoke.py

- **decision_id:** decision_scripts__run_testnet_order_smoke_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** high_risk_retain_until_evidence_and_approval
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_signal_testnet_trial.py

- **decision_id:** decision_scripts__run_signal_testnet_trial_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** high_risk_retain_until_evidence_and_approval
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_spot_testnet_acceptance.py

- **decision_id:** decision_scripts__run_spot_testnet_acceptance_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** high_risk_retain_until_evidence_and_approval
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/safe_flatten_testnet_symbol.py

- **decision_id:** decision_scripts__safe_flatten_testnet_symbol_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** high_risk_retain_until_evidence_and_approval
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/replay_shadow_order_plans_as_testnet_dry.py

- **decision_id:** decision_scripts__replay_shadow_order_plans_as_testnet_dry_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** high_risk_retain_until_evidence_and_approval
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/submit_replayed_testnet_payload.py

- **decision_id:** decision_scripts__submit_replayed_testnet_payload_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** high_risk_retain_until_evidence_and_approval
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_controlled_testnet_shift.py

- **decision_id:** decision_scripts__run_controlled_testnet_shift_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_daily_shadow_scan_pipeline.py

- **decision_id:** decision_scripts__run_daily_shadow_scan_pipeline_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_next_shadow_experiment_plan.py

- **decision_id:** decision_scripts__run_next_shadow_experiment_plan_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_observation_shift_runtime.py

- **decision_id:** decision_scripts__run_observation_shift_runtime_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_remediation_shadow_only_loop.py

- **decision_id:** decision_scripts__run_remediation_shadow_only_loop_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_replay_submit_batch.py

- **decision_id:** decision_scripts__run_replay_submit_batch_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_right_breakout_param_observation.py

- **decision_id:** decision_scripts__run_right_breakout_param_observation_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_right_breakout_scan_dry.py

- **decision_id:** decision_scripts__run_right_breakout_scan_dry_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_shadow_observation_experiments.py

- **decision_id:** decision_scripts__run_shadow_observation_experiments_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_shadow_sample_collection_pipeline.py

- **decision_id:** decision_scripts__run_shadow_sample_collection_pipeline_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/run_shadow_universe_collector.py

- **decision_id:** decision_scripts__run_shadow_universe_collector_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/verify_risk_release_flow.py

- **decision_id:** decision_scripts__verify_risk_release_flow_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### scripts/verify_testnet_repair_scenarios.py

- **decision_id:** decision_scripts__verify_testnet_repair_scenarios_py
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---

### docs/octopusycc_mouse_trade_plan_2026-05-23_2026-05-30.md

- **decision_id:** decision_docs__octopusycc_mouse_trade_plan_2026-05-23_2026-05-30_md
- **cleanup_classification:** RETAIN
- **decision:** RETAIN_FROZEN
- **decision_reason:** no_approval_must_retain
- **preconditions_met:** False
- **evidence_sufficient:** False
- **approval_obtained:** False
- **blocker_cleared:** False

---
