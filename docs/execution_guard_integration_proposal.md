# Execution Guard Integration Proposal

## Current Status

`core/execution_guards.py` exists and passes 62 focused tests.
No integration with any script or runtime module yet.
All functions are pure, no side effects, fail-closed.
Guard functions implement a layered unlock model (layers 0-5).

## Phased Integration Plan

### Phase 1 — Readonly / Report Wrappers

**Target files:**
- `scripts/run_shadow_universe_collector.py`
- `scripts/run_shadow_sample_collection_pipeline.py`
- `scripts/run_right_breakout_scan_dry.py`
- `scripts/run_right_breakout_param_observation.py`

**Required guard functions:**
- `normalize_execution_mode`
- `read_bool_env`
- `parse_symbol_allowlist`
- `build_execution_guard_report`
- `assert_no_live_mode`
- `assert_dry_run_required`

**Expected fail-closed behavior:**
- Unknown mode raises `ValueError`
- `None` mode raises `ValueError`
- Live mode raises `ExecutionGuardError`
- Report dict always has stable keys

**Required tests before touching scripts:**
- Unit tests for each target script's entry point with mock env
- Integration test that `build_execution_guard_report` output matches expected shape
- Regression: existing 62 tests still pass

**Rollback policy:**
- Delete wrapper calls, revert to bare `main()`
- No structural changes to `execution_guards.py`

---

### Phase 2 — Payload Builders

**Target files:**
- `scripts/run_signal_testnet_trial.py`
- `scripts/run_observation_shift_runtime.py`
- `scripts/run_next_shadow_experiment_plan.py`

**Required guard functions:**
- `assert_submit_unlocked`
- `assert_symbol_allowed`
- `parse_symbol_allowlist`
- `build_execution_guard_report`

**Expected fail-closed behavior:**
- Any missing unlock layer raises `ExecutionGuardError`
- Symbol not in allowlist raises `ExecutionGuardError`
- QQ_NO_SUBMIT=1 blocks payload build even if all layers pass

**Required tests before touching scripts:**
- Test that payload builder raises on kill-switch
- Test that payload builder raises on missing layer1-layer5
- Test that allowed symbol passes all layers
- Test that blocked symbol raises at layer5

**Rollback policy:**
- Remove guard calls from payload builders
- Restore `assert_submit_unlocked` as no-op stub
- No changes to `execution_guards.py`

---

### Phase 3 — HIGH_RISK_WRITE Scripts

**Target files:**
- `scripts/submit_approved_candidates.py`
- `scripts/submit_replayed_testnet_payload.py`
- `scripts/run_replay_submit_batch.py`
- `scripts/safe_flatten_testnet_symbol.py`
- `scripts/run_spot_testnet_acceptance.py`
- `scripts/run_testnet_order_smoke.py`
- `scripts/verify_testnet_repair_scenarios.py`

**Required guard functions:**
- `assert_submit_unlocked`
- `assert_cancel_unlocked`
- `assert_flatten_unlocked`
- `assert_dry_run_required`
- `assert_symbol_allowed`
- `build_execution_guard_report`

**Expected fail-closed behavior:**
- All 5 layers (layered unlock) checked before any write
- QQ_NO_SUBMIT kills submit path
- QQ_NO_CANCEL kills cancel path
- QQ_NO_FLATTEN kills flatten path
- QQ_NO_LIVE blocks live-mode writes
- QQ_REQUIRE_DRY_RUN enforced unless all unlock layers pass
- Guard report logged before execution

**Required tests before touching scripts:**
- Full integration test: script entry + guard call + mock exchange
- Kill-switch test: each QQ_NO_* blocks corresponding action
- Layer1-layer5 rejection test per action
- Rollback test: guard removal restores original behavior

**Rollback policy:**
- Wrap guard calls in try/except, log warning on removal
- Keep `execution_guards.py` unchanged
- Script falls back to old behavior on guard import failure

---

### Phase 4 — HIGH_RISK_RUNTIME Orchestrators

**Target files:**
- `core/live_runner.py`
- `scripts/live_playbook.py`
- `scripts/run_controlled_testnet_shift.py`
- `scripts/run_daily_shadow_scan_pipeline.py`
- `scripts/run_remediation_shadow_only_loop.py`
- `scripts/run_shadow_observation_experiments.py`
- `scripts/verify_risk_release_flow.py`

**Required guard functions:**
- All T601 + T602 functions
- `build_execution_guard_report` (logged at startup + per-action)
- Custom runtime gate (see `docs/runtime_gate_design.md`)

**Expected fail-closed behavior:**
- Runtime startup blocked if mode unknown or live
- Per-action guard checked before each exchange call
- Child processes inherit QQ_NO_* env vars
- Guard report emitted at startup and logged to file
- Runtime preflight checklist enforced

**Required tests before touching scripts:**
- Full runtime integration test (dry-run only)
- Subprocess env inheritance test
- Runtime guard report shape validation
- Failure scenario: all layers fail, no exchange call made

**Rollback policy:**
- Guard calls in try/except with warning log
- Runtime falls back to old safety_switch behavior
- No changes to `execution_guards.py` core logic
