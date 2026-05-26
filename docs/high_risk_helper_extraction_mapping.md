# High-Risk Helper Extraction Mapping

All migration targets use fail-closed semantics.
Guard functions implement a layered unlock model (layers 0-5).
Guard report shape must be validated before script integration.

## HIGH_RISK_WRITE

Kill-switch env vars for HIGH_RISK_WRITE: QQ_NO_SUBMIT, QQ_NO_CANCEL, QQ_NO_FLATTEN.
QQ_REQUIRE_DRY_RUN enforced unless full layered unlock passes.

### scripts/submit_approved_candidates.py
- **Risk class:** HIGH_RISK_WRITE
- **Likely duplicate pattern:** env loading, mode check, guard call
- **Candidate helper:** `assert_submit_unlocked`, `assert_dry_run_required`, `build_execution_guard_report`
- **Migration phase:** Phase 3
- **Do-not-touch reason:** writes testnet orders, any bug can submit unintended trades
- **Proposed future test file:** `tests/integration/test_submit_candidates_guards.py`

### scripts/submit_replayed_testnet_payload.py
- **Risk class:** HIGH_RISK_WRITE
- **Likely duplicate pattern:** payload validation, mode check, symbol check
- **Candidate helper:** `assert_submit_unlocked`, `assert_symbol_allowed`, `parse_symbol_allowlist`
- **Migration phase:** Phase 3
- **Do-not-touch reason:** replays order payloads, wrong guard can cause duplicate submissions
- **Proposed future test file:** `tests/integration/test_replay_payload_guards.py`

### scripts/run_replay_submit_batch.py
- **Risk class:** HIGH_RISK_WRITE
- **Likely duplicate pattern:** batch mode check, guard per symbol
- **Candidate helper:** `assert_submit_unlocked`, `assert_symbol_allowed`, `build_execution_guard_report`
- **Migration phase:** Phase 3
- **Do-not-touch reason:** batch submission, guard failure can cause multiple unintended orders
- **Proposed future test file:** `tests/integration/test_replay_batch_guards.py`

### scripts/safe_flatten_testnet_symbol.py
- **Risk class:** HIGH_RISK_WRITE
- **Likely duplicate pattern:** flatten guard, symbol allowlist, mode check
- **Candidate helper:** `assert_flatten_unlocked`, `assert_symbol_allowed`, `assert_dry_run_required`
- **Migration phase:** Phase 3
- **Do-not-touch reason:** flatten closes positions, wrong guard can flatten live positions
- **Proposed future test file:** `tests/integration/test_flatten_guards.py`

### scripts/run_spot_testnet_acceptance.py
- **Risk class:** HIGH_RISK_WRITE
- **Likely duplicate pattern:** acceptance test mode, guard per order
- **Candidate helper:** `assert_submit_unlocked`, `assert_dry_run_required`
- **Migration phase:** Phase 3
- **Do-not-touch reason:** acceptance test submits real testnet orders, guard failure leaks to live
- **Proposed future test file:** `tests/integration/test_acceptance_guards.py`

### scripts/run_testnet_order_smoke.py
- **Risk class:** HIGH_RISK_WRITE
- **Likely duplicate pattern:** smoke test mode, minimal guard
- **Candidate helper:** `assert_submit_unlocked`, `assert_dry_run_required`
- **Migration phase:** Phase 3
- **Do-not-touch reason:** smoke test can accidentally submit live orders
- **Proposed future test file:** `tests/integration/test_smoke_guards.py`

### scripts/run_signal_testnet_trial.py
- **Risk class:** HIGH_RISK_WRITE
- **Likely duplicate pattern:** trial mode, signal-to-order guard
- **Candidate helper:** `assert_submit_unlocked`, `assert_symbol_allowed`, `build_execution_guard_report`
- **Migration phase:** Phase 2-3
- **Do-not-touch reason:** signal trial can escalate to order submission
- **Proposed future test file:** `tests/integration/test_signal_trial_guards.py`

### scripts/verify_testnet_repair_scenarios.py
- **Risk class:** HIGH_RISK_WRITE
- **Likely duplicate pattern:** repair scenario mode, order modification guard
- **Candidate helper:** `assert_cancel_unlocked`, `assert_submit_unlocked`
- **Migration phase:** Phase 3
- **Do-not-touch reason:** repair can cancel/replace orders, wrong guard causes unintended state
- **Proposed future test file:** `tests/integration/test_repair_guards.py`

---

## HIGH_RISK_RUNTIME

Kill-switch env vars for HIGH_RISK_RUNTIME: QQ_NO_SUBMIT, QQ_NO_CANCEL, QQ_NO_FLATTEN, QQ_NO_LIVE.
Guard report must be emitted at startup and logged for all runtime orchestrators.
QQ_REQUIRE_DRY_RUN enforced by default.

### core/live_runner.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** runtime mode check, safety_switch guard
- **Candidate helper:** `assert_no_live_mode`, `build_execution_guard_report`, `normalize_execution_mode`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** core runtime loop, any guard bug halts all trading
- **Proposed future test file:** `tests/integration/test_live_runner_guards.py`

### scripts/live_playbook.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** playbook mode, runtime guard per step
- **Candidate helper:** `assert_no_live_mode`, `assert_submit_unlocked`, `build_execution_guard_report`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** orchestrates live actions, guard failure can cascade
- **Proposed future test file:** `tests/integration/test_live_playbook_guards.py`

### scripts/replay_shadow_order_plans_as_testnet_dry.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** shadow replay mode, dry-run check
- **Candidate helper:** `assert_dry_run_required`, `build_execution_guard_report`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** shadow replay can accidentally submit live
- **Proposed future test file:** `tests/integration/test_shadow_replay_guards.py`

### scripts/run_controlled_testnet_shift.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** testnet shift mode, env check
- **Candidate helper:** `assert_no_live_mode`, `assert_submit_unlocked`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** controlled shift can escalate to live mode
- **Proposed future test file:** `tests/integration/test_testnet_shift_guards.py`

### scripts/run_daily_shadow_scan_pipeline.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** pipeline mode, readonly check
- **Candidate helper:** `assert_dry_run_required`, `assert_no_live_mode`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** daily pipeline runs unattended, guard failure has delayed detection
- **Proposed future test file:** `tests/integration/test_shadow_scan_guards.py`

### scripts/run_next_shadow_experiment_plan.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** experiment plan mode, dry-run check
- **Candidate helper:** `assert_dry_run_required`, `build_execution_guard_report`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** experiment plan can trigger live experiments
- **Proposed future test file:** `tests/integration/test_experiment_plan_guards.py`

### scripts/run_observation_shift_runtime.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** observation mode, runtime guard
- **Candidate helper:** `assert_no_live_mode`, `build_execution_guard_report`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** observation shift can accidentally modify positions
- **Proposed future test file:** `tests/integration/test_observation_guards.py`

### scripts/run_remediation_shadow_only_loop.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** remediation loop mode, guard per iteration
- **Candidate helper:** `assert_dry_run_required`, `assert_no_live_mode`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** loop runs continuously, guard failure has prolonged exposure
- **Proposed future test file:** `tests/integration/test_remediation_guards.py`

### scripts/run_right_breakout_param_observation.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** param observation mode, readonly check
- **Candidate helper:** `assert_dry_run_required`, `assert_no_live_mode`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** parameter observation can trigger live if guard missing
- **Proposed future test file:** `tests/integration/test_breakout_param_guards.py`

### scripts/run_right_breakout_scan_dry.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** scan mode, dry-run check
- **Candidate helper:** `assert_dry_run_required`, `assert_no_live_mode`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** scan can escalate to live mode without guard
- **Proposed future test file:** `tests/integration/test_breakout_scan_guards.py`

### scripts/run_shadow_observation_experiments.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** experiment mode, runtime guard
- **Candidate helper:** `assert_no_live_mode`, `build_execution_guard_report`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** experiments can trigger live if guard missing
- **Proposed future test file:** `tests/integration/test_shadow_experiment_guards.py`

### scripts/run_shadow_sample_collection_pipeline.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** collection mode, readonly check
- **Candidate helper:** `assert_dry_run_required`, `assert_no_live_mode`
- **Migration phase:** Phase 1-4
- **Do-not-touch reason:** collection pipeline can escalate to live
- **Proposed future test file:** `tests/integration/test_sample_collection_guards.py`

### scripts/run_shadow_universe_collector.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** collector mode, readonly check
- **Candidate helper:** `assert_dry_run_required`, `assert_no_live_mode`
- **Migration phase:** Phase 1-4
- **Do-not-touch reason:** universe collector runs unattended
- **Proposed future test file:** `tests/integration/test_universe_collector_guards.py`

### scripts/verify_risk_release_flow.py
- **Risk class:** HIGH_RISK_RUNTIME
- **Likely duplicate pattern:** release verification mode, guard check
- **Candidate helper:** `assert_no_live_mode`, `build_execution_guard_report`
- **Migration phase:** Phase 4
- **Do-not-touch reason:** release flow verification can accidentally enable live
- **Proposed future test file:** `tests/integration/test_risk_release_guards.py`
