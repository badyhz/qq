# Execution Guard Phase2 Validation Plan

## 1. Scope

| Batch | Scripts | Status | Tests |
|---|---|---|---|
| Batch2 | 5 scripts (validate_testnet_artifacts, generate_runner_dry_run_report, generate_gate_decision_dashboard, generate_trading_system_health_dashboard, generate_sample_collection_eod_report) | **COMPLETED** | 30/30 pass |
| Batch3 | 5 scripts (analyze_post_entry_mfe_mae, analyze_trade_lifecycle_performance, evaluate_missing_klines_recovery, evaluate_tp_sl_efficiency, show_trade_stats) | **UPCOMING** | 30 expected |
| Batch4 | 5 promoted SAFE scripts (T636 shortlist TBD) | **FUTURE** | 30 expected |

### Batch3 Target Scripts

| # | Script | Guard Function | Test File (expected) |
|---|---|---|---|
| 1 | `scripts/analyze_post_entry_mfe_mae.py` | `assert_dry_run_required` | `tests/unit/test_analyze_post_entry_mfe_mae_guard.py` |
| 2 | `scripts/analyze_trade_lifecycle_performance.py` | `assert_dry_run_required` | `tests/unit/test_analyze_trade_lifecycle_performance_guard.py` |
| 3 | `scripts/evaluate_missing_klines_recovery.py` | `assert_dry_run_required` | `tests/unit/test_evaluate_missing_klines_recovery_guard.py` |
| 4 | `scripts/evaluate_tp_sl_efficiency.py` | `assert_dry_run_required` | `tests/unit/test_evaluate_tp_sl_efficiency_guard.py` |
| 5 | `scripts/show_trade_stats.py` | `assert_dry_run_required` | `tests/unit/test_show_trade_stats_guard.py` |

---

## 2. Required Test Matrix Per Script

Each guarded script must pass all 6 tests:

| Test | Description |
|---|---|
| `test_import_safe` | Module loads without error; exposes `main` + core function |
| `test_no_high_risk_imports` | Source has no forbidden imports (ccxt, requests to exchange, websocket) |
| `test_default_dry_run_allowed` | Missing `QQ_RUNTIME_MODE` env → `ValueError` |
| `test_dry_run_mode_allowed` | `QQ_RUNTIME_MODE=dry_run` → passes |
| `test_live_mode_blocked` | `QQ_RUNTIME_MODE=live` → `ExecutionGuardError` |
| `test_unknown_mode_blocked` | `QQ_RUNTIME_MODE=foobar` → `ValueError` |

**Per batch:** 5 scripts x 6 tests = **30 tests**

---

## 3. Required Regression Suite

These tests must remain green before and after every batch:

| Test File | Cases | Purpose |
|---|---|---|
| `tests/unit/test_execution_guards.py` | 62 | Pure helper tests |
| `tests/unit/test_execution_guard_schema.py` | 38 | Schema validation tests |
| `tests/unit/test_execution_guard_contract.py` | 24 | Cross-layer contract tests |

**Regression total:** 124 tests (constant across all batches)

---

## 4. Required Git Diff Checks

After each batch commit, run and verify:

```bash
# Only guarded scripts + test files should appear
git diff --stat

# 22 frozen files must remain ?? (untracked)
git status --short

# core/live_runner.py must show zero changes
git diff core/live_runner.py
```

**Expected `git diff --stat` per batch:**
- Modified: 5 target scripts (guard injection)
- Added: 5 new test files

**Expected `git status --short`:**
- 22 frozen files remain `??` (untracked, untouched)
- `core/live_runner.py` shows no modification

---

## 5. Frozen Boundary Checks

Run before and after each batch:

```bash
# Verify 22 frozen files unchanged
git diff -- scripts/submit_approved_candidates.py
git diff -- scripts/submit_replayed_testnet_payload.py
git diff -- scripts/run_replay_submit_batch.py
git diff -- scripts/safe_flatten_testnet_symbol.py
git diff -- scripts/run_spot_testnet_acceptance.py
git diff -- scripts/run_testnet_order_smoke.py
git diff -- scripts/verify_testnet_repair_scenarios.py
git diff -- core/live_runner.py
git diff -- scripts/live_playbook.py
git diff -- scripts/replay_shadow_order_plans_as_testnet_dry.py
git diff -- scripts/run_controlled_testnet_shift.py
git diff -- scripts/run_daily_shadow_scan_pipeline.py
git diff -- scripts/run_next_shadow_experiment_plan.py
git diff -- scripts/run_observation_shift_runtime.py
git diff -- scripts/run_remediation_shadow_only_loop.py
git diff -- scripts/run_right_breakout_param_observation.py
git diff -- scripts/run_right_breakout_scan_dry.py
git diff -- scripts/run_shadow_observation_experiments.py
git diff -- scripts/run_shadow_sample_collection_pipeline.py
git diff -- scripts/run_shadow_universe_collectory.py
git diff -- scripts/run_signal_testnet_trial.py
git diff -- scripts/live_playbook.py
```

### Boundary Invariants

| Check | Rule |
|---|---|
| 22 frozen files | Zero diff before AND after batch |
| `core/live_runner.py` | Zero diff — always frozen |
| Runtime integration | NO imports from guard modules into runtime path |
| Planner integration | NO guard logic added to planner/scheduler modules |

---

## 6. Rollback Criteria

| Trigger | Action |
|---|---|
| Any test failure (guard or regression) | **ROLLBACK** that batch |
| Any frozen file modification detected | **ROLLBACK** + **ALERT** |
| Any new exchange/order imports introduced | **ROLLBACK** + **ALERT** |
| `core/live_runner.py` modified | **ROLLBACK** + **ALERT** |

### Rollback Command

```bash
git revert HEAD   # or git reset --hard <pre-batch-tag>
```

---

## 7. PASS / PARTIAL / FAIL Rules

| Verdict | Criteria |
|---|---|
| **PASS** | All 6 guard tests + 124 regression tests green; zero frozen file changes; zero new exchange imports |
| **PARTIAL** | Some tests fail but frozen boundary intact; no frozen file modifications |
| **FAIL** | Frozen file modified OR exchange/order imports introduced in guarded scripts |

---

## 8. Test Count Summary

| Scope | Tests | Status |
|---|---|---|
| Batch2 (5 scripts) | 30 | 30/30 PASS (completed) |
| Batch3 (5 scripts) | 30 | Upcoming |
| Batch4 (5 scripts) | 30 | Future |
| Regression suite | 124 | Constant |
| **Total per batch validation** | **154** | (30 batch + 124 regression) |

### Cumulative After All Batches

| Metric | Value |
|---|---|
| Guarded scripts total | 15 (3 batches x 5) |
| Guard-specific tests | 90 (15 x 6) |
| Regression tests | 124 (constant) |
| **Grand total** | **214** |

---

## 9. Hard Constraints

- docs only — no code changes beyond test files
- NO guard injection into non-target scripts
- NO runtime integration
- NO planner integration
- DO NOT TOUCH 22 frozen files
- DO NOT TOUCH `core/live_runner.py`
