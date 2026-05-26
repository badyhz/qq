# Execution Guard Phase2 SAFE BATCH Runbook

## 1. Purpose

Operational reference for the **Execution Guard Phase2 SAFE BATCH** milestone.

Phase2 covers guard integration into **non-frozen, SAFE_READONLY** scripts only. Each script receives `assert_dry_run_required` at its CLI entry point. No HIGH_RISK files are touched. No runtime or planner integration occurs.

---

## 2. Current Milestone

| Field | Value |
|---|---|
| HEAD | `71e34ca` |
| Tag | `execution-guard-phase1-frozen` |
| Tag | `execution-guard-phase2-safe-batch` |
| Phase status | Phase0 COMPLETE, Phase1 COMPLETE, Phase2 SAFE BATCH COMPLETE (41 scripts) |
| Frozen boundary | Phase3–4 FROZEN — NO UNFREEZE |

---

## 3. Guard Contract

All Phase2 scripts use the same entry-point guard:

```python
from core.execution_guards import assert_dry_run_required

mode = normalize_execution_mode(
    os.environ.get("QQ_RUNTIME_MODE")
)
assert_dry_run_required(mode)
```

**Rules:**
- CLI `main()` entry only — guard runs before any logic.
- `QQ_RUNTIME_MODE` is the sole mode source.
- `normalize_execution_mode` raises `ValueError` for unknown/missing modes.
- `assert_dry_run_required` raises `ExecutionGuardError` if mode is not `dry_run`.
- **No implicit dry_run fallback.**

---

## 4. Runtime Behavior Matrix

| Case | Input | Result |
|---|---|---|
| dry_run | `QQ_RUNTIME_MODE=dry_run` | **PASS** |
| live | `QQ_RUNTIME_MODE=live` | **ExecutionGuardError** |
| testnet | `QQ_RUNTIME_MODE=testnet` | **ExecutionGuardError** |
| missing env | `QQ_RUNTIME_MODE` unset | **ValueError** |
| bogus mode | `QQ_RUNTIME_MODE=foobar` | **ValueError** |
| empty string | `QQ_RUNTIME_MODE=` | **ValueError** |

**Policy:** FAIL-CLOSED. No implicit dry_run fallback. No silent pass-through.

---

## 5. Guarded Scripts Inventory

### Phase2 Safe Scripts (41)

| # | Script | Guard Function | Test File | Commit |
|---|---|---|---|---|
| 1 | `scripts/validate_testnet_artifacts.py` | `assert_dry_run_required` | `tests/unit/test_validate_testnet_artifacts_guard.py` | `f4cfba0` |
| 2 | `scripts/generate_runner_dry_run_report.py` | `assert_dry_run_required` | `tests/unit/test_generate_runner_dry_run_report_guard.py` | `9ece5b1` |
| 3 | `scripts/generate_gate_decision_dashboard.py` | `assert_dry_run_required` | `tests/unit/test_generate_gate_decision_dashboard_guard.py` | `8bf2181` |
| 4 | `scripts/generate_trading_system_health_dashboard.py` | `assert_dry_run_required` | `tests/unit/test_generate_trading_system_health_dashboard_guard.py` | `e45905e` |
| 5 | `scripts/generate_sample_collection_eod_report.py` | `assert_dry_run_required` | `tests/unit/test_generate_sample_collection_eod_report_guard.py` | `cab8e95` |
| 6 | `scripts/audit_real_ohlcv_source_schema.py` | `assert_dry_run_required` | `tests/unit/test_audit_real_ohlcv_source_schema_guard.py` | T627 |
| 7 | `scripts/calculate_execution_quality_score.py` | `assert_dry_run_required` | `tests/unit/test_calculate_execution_quality_score_guard.py` | T627 |
| 8 | `scripts/generate_ohlcv_gap_validation_control_report_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_ohlcv_gap_validation_control_report_v1_guard.py` | T627 |
| 9 | `scripts/generate_real_ohlcv_source_mapping_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_real_ohlcv_source_mapping_v1_guard.py` | T627 |
| 10 | `scripts/validate_real_ohlcv_gap_candidates.py` | `assert_dry_run_required` | `tests/unit/test_validate_real_ohlcv_gap_candidates_guard.py` | T627 |
| 11 | `scripts/analyze_post_entry_mfe_mae.py` | `assert_dry_run_required` | `tests/unit/test_analyze_post_entry_mfe_mae_guard.py` | T635 |
| 12 | `scripts/analyze_trade_lifecycle_performance.py` | `assert_dry_run_required` | `tests/unit/test_analyze_trade_lifecycle_performance_guard.py` | T635 |
| 13 | `scripts/evaluate_missing_klines_recovery.py` | `assert_dry_run_required` | `tests/unit/test_evaluate_missing_klines_recovery_guard.py` | T635 |
| 14 | `scripts/evaluate_tp_sl_efficiency.py` | `assert_dry_run_required` | `tests/unit/test_evaluate_tp_sl_efficiency_guard.py` | T635 |
| 15 | `scripts/show_trade_stats.py` | `assert_dry_run_required` | `tests/unit/test_show_trade_stats_guard.py` | T635 |
| 16 | `scripts/generate_daily_operator_checklist.py` | `assert_dry_run_required` | `tests/unit/test_generate_daily_operator_checklist_guard.py` | T640 |
| 17 | `scripts/audit_price_field_source_trust.py` | `assert_dry_run_required` | `tests/unit/test_audit_price_field_source_trust_guard.py` | T640 |
| 18 | `scripts/generate_phase_control_report_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_phase_control_report_v1_guard.py` | T640 |
| 19 | `scripts/generate_phase_control_report_v2.py` | `assert_dry_run_required` | `tests/unit/test_generate_phase_control_report_v2_guard.py` | T640 |
| 20 | `scripts/generate_strategy_relaxation_suggestions.py` | `assert_dry_run_required` | `tests/unit/test_generate_strategy_relaxation_suggestions_guard.py` | T640 |
| 21 | `scripts/analyze_readiness_blocker_attribution.py` | `assert_dry_run_required` | `tests/unit/test_analyze_readiness_blocker_attribution_guard.py` | T645 |
| 22 | `scripts/diagnose_near_miss_strict_gap.py` | `assert_dry_run_required` | `tests/unit/test_diagnose_near_miss_strict_gap_guard.py` | T645 |
| 23 | `scripts/evaluate_strategy_promotion_rules.py` | `assert_dry_run_required` | `tests/unit/test_evaluate_strategy_promotion_rules_guard.py` | T645 |
| 24 | `scripts/generate_single_human_gated_execution_local_audit_manifest_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_single_human_gated_execution_local_audit_manifest_v1_guard.py` | T645 |
| 25 | `scripts/map_readiness_blockers_to_actions.py` | `assert_dry_run_required` | `tests/unit/test_map_readiness_blockers_to_actions_guard.py` | T645 |
| 26 | `scripts/generate_human_confirmation_token_gate_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_human_confirmation_token_gate_v1_guard.py` | T666 |
| 27 | `scripts/generate_human_gated_execution_final_safety_gate_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_human_gated_execution_final_safety_gate_v1_guard.py` | T666 |
| 28 | `scripts/generate_human_gated_execution_wrapper_eligibility_report_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_human_gated_execution_wrapper_eligibility_report_v1_guard.py` | T666 |
| 29 | `scripts/generate_human_gated_execution_wrapper_phase_control_report_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_human_gated_execution_wrapper_phase_control_report_v1_guard.py` | T666 |
| 30 | `scripts/generate_single_human_gated_execution_command_preview_packet_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_single_human_gated_execution_command_preview_packet_v1_guard.py` | T666 |
| 31 | `scripts/generate_single_human_gated_execution_wrapper_artifact_phase_control_report_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_single_human_gated_execution_wrapper_artifact_phase_control_report_v1_guard.py` | T681 |
| 32 | `scripts/generate_single_human_gated_testnet_execution_wrapper_artifact_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_single_human_gated_testnet_execution_wrapper_artifact_v1_guard.py` | T681 |
| 33 | `scripts/generate_ohlcv_gap_manual_approval_artifact_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_ohlcv_gap_manual_approval_artifact_v1_guard.py` | T681 |
| 34 | `scripts/generate_ohlcv_gap_manual_approval_gate_report_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_ohlcv_gap_manual_approval_gate_report_v1_guard.py` | T681 |
| 35 | `scripts/generate_ohlcv_gap_manual_review_packet_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_ohlcv_gap_manual_review_packet_v1_guard.py` | T681 |
| 36 | `scripts/generate_ohlcv_gap_manual_review_phase_control_report_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_ohlcv_gap_manual_review_phase_control_report_v1_guard.py` | T684 |
| 37 | `scripts/interpret_ohlcv_gap_manual_review_checklist_v1.py` | `assert_dry_run_required` | `tests/unit/test_interpret_ohlcv_gap_manual_review_checklist_v1_guard.py` | T684 |
| 38 | `scripts/generate_repeat_small_batch_candidate_refresh_packet_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_repeat_small_batch_candidate_refresh_packet_v1_guard.py` | T684 |
| 39 | `scripts/generate_human_copy_paste_dry_run_readiness_packet_v1.py` | `assert_dry_run_required` | `tests/unit/test_generate_human_copy_paste_dry_run_readiness_packet_v1_guard.py` | T684 |
| 40 | `scripts/verify_human_copy_paste_dry_run_command_v1.py` | `assert_dry_run_required` | `tests/unit/test_verify_human_copy_paste_dry_run_command_v1_guard.py` | T684 |
| 41 | `scripts/simulate_human_token_validation_v1.py` | `assert_dry_run_required` | `tests/unit/test_simulate_human_token_validation_v1_guard.py` | T684 |

### Core Guard Modules (Phase0)

| File | Purpose |
|---|---|
| `core/execution_guards.py` | Pure helpers + layered unlock assertions |
| `core/execution_guard_schema.py` | Schema validation + summary formatting |

### Contract Tests (Phase0)

| File | Coverage |
|---|---|
| `tests/unit/test_execution_guards.py` | Pure helper tests (62 cases) |
| `tests/unit/test_execution_guard_schema.py` | Schema tests (38 cases) |
| `tests/unit/test_execution_guard_contract.py` | Cross-layer contract (20 cases) |
| `tests/unit/test_generate_execution_guard_status_report.py` | Wrapper tests (31 cases) |

### Test Baseline

| Scope | Tests | Status |
|---|---|---|
| Guard core (Phase0) | 124 | 124/124 pass |
| Phase2 batch1 (5 scripts) | 30 | 30/30 pass |
| Phase2 batch2 (5 scripts) | 30 | 30/30 pass |
| Phase2 batch3 (5 scripts) | 30 | 24 pass + 6 skipped (show_trade_stats pre-existing broken import) |
| Phase2 batch4 (5 scripts) | 30 | 30/30 pass |
| Phase2 batch5 (5 scripts) | 30 | 30/30 pass |
| Phase2 batch6 (5 scripts) | 30 | 30/30 pass |
| Phase2 batch7 (5 scripts) | 30 | 30/30 pass |
| Phase2 batch8 (5 scripts) | 30 | 30/30 pass |
| Phase2 batch9 (1 script) | 6 | 6/6 pass |
| Total guard tests | ~374 | ~374 pass |

---

## 6. Frozen Boundary

### 22 Frozen Files

**HIGH_RISK_WRITE (7):**
1. `scripts/submit_approved_candidates.py`
2. `scripts/submit_replayed_testnet_payload.py`
3. `scripts/run_replay_submit_batch.py`
4. `scripts/safe_flatten_testnet_symbol.py`
5. `scripts/run_spot_testnet_acceptance.py`
6. `scripts/run_testnet_order_smoke.py`
7. `scripts/verify_testnet_repair_scenarios.py`

**HIGH_RISK_RUNTIME (15):**
1. `core/live_runner.py`
2. `scripts/live_playbook.py`
3. `scripts/replay_shadow_order_plans_as_testnet_dry.py`
4. `scripts/run_controlled_testnet_shift.py`
5. `scripts/run_daily_shadow_scan_pipeline.py`
6. `scripts/run_next_shadow_experiment_plan.py`
7. `scripts/run_observation_shift_runtime.py`
8. `scripts/run_remediation_shadow_only_loop.py`
9. `scripts/run_replay_submit_batch.py`
10. `scripts/run_right_breakout_param_observation.py`
11. `scripts/run_right_breakout_scan_dry.py`
12. `scripts/run_shadow_observation_experiments.py`
13. `scripts/run_shadow_sample_collection_pipeline.py`
14. `scripts/run_shadow_universe_collector.py`
15. `scripts/run_signal_testnet_trial.py`

### Policy

- **NO UNFREEZE** without explicit review + approval.
- **NO runtime integration** — `core/live_runner.py` remains frozen.
- **NO planner escalation** — planner path remains frozen.
- **NO code changes** to frozen files — readonly audits only.

---

## 7. Example Commands

### PASS (dry_run)

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/validate_testnet_artifacts.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_runner_dry_run_report.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_gate_decision_dashboard.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_trading_system_health_dashboard.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_sample_collection_eod_report.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/audit_real_ohlcv_source_schema.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/calculate_execution_quality_score.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_ohlcv_gap_validation_control_report_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_real_ohlcv_source_mapping_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/validate_real_ohlcv_gap_candidates.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/analyze_post_entry_mfe_mae.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/analyze_trade_lifecycle_performance.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/evaluate_missing_klines_recovery.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/evaluate_tp_sl_efficiency.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/show_trade_stats.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_daily_operator_checklist.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/audit_price_field_source_trust.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_phase_control_report_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_phase_control_report_v2.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_strategy_relaxation_suggestions.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/analyze_readiness_blocker_attribution.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/diagnose_near_miss_strict_gap.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/evaluate_strategy_promotion_rules.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_single_human_gated_execution_local_audit_manifest_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/map_readiness_blockers_to_actions.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_human_confirmation_token_gate_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_human_gated_execution_final_safety_gate_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_human_gated_execution_wrapper_eligibility_report_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_human_gated_execution_wrapper_phase_control_report_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_single_human_gated_execution_command_preview_packet_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_ohlcv_gap_manual_review_phase_control_report_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/interpret_ohlcv_gap_manual_review_checklist_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_repeat_small_batch_candidate_refresh_packet_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/generate_human_copy_paste_dry_run_readiness_packet_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/verify_human_copy_paste_dry_run_command_v1.py
```

```bash
QQ_RUNTIME_MODE=dry_run \
PYTHONPATH=. .venv/bin/python scripts/simulate_human_token_validation_v1.py
```

### BLOCKED (live)

```bash
QQ_RUNTIME_MODE=live \
PYTHONPATH=. .venv/bin/python scripts/validate_testnet_artifacts.py
# → ExecutionGuardError: dry_run required, got 'live'
```

### BLOCKED (missing env)

```bash
PYTHONPATH=. .venv/bin/python scripts/validate_testnet_artifacts.py
# → ValueError: unknown execution mode: ''
```

---

## 8. Rollback / Provenance

### Key Commits

| Commit | Description |
|---|---|
| `ec3e8a9` | test: tighten execution guard report contract |
| `f4cfba0` | feat: guard testnet artifact validator |
| `9ece5b1` | feat: guard runner dry-run report |
| `8bf2181` | feat: guard gate decision dashboard |
| `e45905e` | feat: guard trading system health dashboard |
| `cab8e95` | feat: guard sample collection eod report |
| `71e34ca` | docs: record phase2 safe batch completion |

### Tags

| Tag | Commit | Description |
|---|---|---|
| `execution-guard-phase1-frozen` | `977a983` | Phase0-1 complete; 22 high-risk files frozen |
| `execution-guard-phase2-safe-batch` | `71e34ca` | Phase2 safe batch complete; 35 non-frozen scripts guarded |

### Rollback

To revert to pre-Phase2 state:

```bash
git checkout execution-guard-phase1-frozen
```

This restores the codebase to the point where only Phase0 helpers and Phase1 docs existed, before any safe-script guard integrations.
