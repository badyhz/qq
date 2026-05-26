# Execution Guard Integration Matrix

## Legend

| Status | Meaning |
|---|---|
| **Completed** | Implemented, tested, no further work needed |
| **Planned** | Designed but not yet implemented |
| **Blocked** | Waiting on prior phase or explicit unfreeze |
| **Frozen** | HIGH_RISK script; no modification until explicit unfreeze + review |

## Phase0 — Helper / Schema / Contract (completed)

**Scope**: Pure functions, schema validation, report generation, contract tests.

**Allowed targets**:
- `core/execution_guards.py` — pure helpers
- `core/execution_guard_schema.py` — schema validation + summary
- `scripts/generate_execution_guard_status_report.py` — readonly CLI wrapper
- `tests/unit/test_execution_guards.py` — helper tests
- `tests/unit/test_execution_guard_schema.py` — schema tests
- `tests/unit/test_execution_guard_contract.py` — contract tests
- `tests/unit/test_generate_execution_guard_status_report.py` — wrapper tests
- `docs/execution_guard_report_examples.md` — JSON examples
- `docs/execution_guard_integration_matrix.md` — this file

**Forbidden targets**: All 21 frozen HIGH_RISK scripts, `core/live_runner.py`, any submit/cancel/flatten chain.

**Acceptance gate**: All tests pass, no high-risk imports, readonly-only.

| Component | File | Implemented | Tested |
|---|---|---|---|
| Pure helpers | `core/execution_guards.py` | yes | yes (62) |
| Schema validation | `core/execution_guard_schema.py` | yes | yes (38) |
| Status report wrapper | `scripts/generate_execution_guard_status_report.py` | yes | yes (31) |
| Contract tests | `tests/unit/test_execution_guard_contract.py` | yes | yes (20) |

---

## Phase1 — Readonly Integration (completed)

**Scope**: CLI usage, docs, runtime integration proposal, readonly wrappers for non-frozen scripts.

**Allowed targets**:
- `scripts/generate_execution_guard_status_report.py` (extend)
- `docs/` (extend)
- New readonly scripts in `scripts/` (non-frozen)

**Forbidden targets**: All 21 frozen HIGH_RISK scripts, `core/live_runner.py`, any submit/cancel/flatten chain.

**Acceptance gate**: CLI validated, docs complete, no high-risk imports, contract tests pass.

| Target | Guard Functions | Status | Tests |
|---|---|---|---|
| CLI polish (`--compact`, `--pretty`) | `generate_report` | done | done |
| Schema drift helper | `get_guard_schema_required_keys` | done | done |
| Summary formatter | `format_guard_summary_text` | done | done |
| Report examples | JSON docs | done | n/a |
| Integration matrix | this file | done | n/a |
| Runtime integration proposal | `docs/` | planned | n/a |

---

## Phase2 — Payload Builders (blocked)

**Scope**: Guard integration into non-frozen payload builder scripts.

**Allowed targets**:
- Non-frozen payload builder scripts (if any exist)
- Guard helper functions

**Forbidden targets**: All 21 frozen HIGH_RISK scripts, `core/live_runner.py`, any submit/cancel/flatten chain.

**Acceptance gate**: Each target has dedicated tests, all guard layers validated, no live-mode leak.

| Target | Required Guards | Status | Tests | Blocker |
|---|---|---|---|---|
| Signal trial | `assert_submit_unlocked` | not started | none | needs Phase1 |
| Observation shift | `assert_submit_unlocked` | not started | none | needs Phase1 |
| Experiment plan | `assert_dry_run_required` | not started | none | needs Phase1 |

---

## Phase3 — HIGH_RISK_WRITE (blocked)

**Scope**: Guard integration into frozen HIGH_RISK_WRITE scripts.

**Allowed targets**: Only after explicit unfreeze + review.

**Forbidden targets**: `core/live_runner.py`, any HIGH_RISK_RUNTIME scripts.

**Acceptance gate**: Full layered unlock validated, kill-switch tested, rollback plan documented.

| Target | Required Guards | Status | Tests | Blocker |
|---|---|---|---|---|
| submit_approved_candidates | `assert_submit_unlocked` | **FROZEN** | none | unfreeze |
| submit_replayed_testnet_payload | `assert_submit_unlocked` | **FROZEN** | none | unfreeze |
| run_replay_submit_batch | `assert_submit_unlocked` | **FROZEN** | none | unfreeze |
| safe_flatten_testnet_symbol | `assert_flatten_unlocked` | **FROZEN** | none | unfreeze |
| run_spot_testnet_acceptance | `assert_submit_unlocked` | **FROZEN** | none | unfreeze |
| run_testnet_order_smoke | `assert_submit_unlocked` | **FROZEN** | none | unfreeze |
| verify_testnet_repair_scenarios | `assert_cancel_unlocked` | **FROZEN** | none | unfreeze |

---

## Phase4 — HIGH_RISK_RUNTIME (blocked)

**Scope**: Guard integration into frozen HIGH_RISK_RUNTIME orchestrators.

**Allowed targets**: Only after explicit unfreeze + review.

**Forbidden targets**: None additional (Phase3 must complete first).

**Acceptance gate**: Runtime guard report emitted, preflight checklist enforced, subprocess env inheritance validated.

| Target | Required Guards | Status | Tests | Blocker |
|---|---|---|---|---|
| live_runner.py | all T601+T602 | **FROZEN** | none | unfreeze |
| live_playbook.py | all T601+T602 | **FROZEN** | none | unfreeze |
| run_controlled_testnet_shift | `assert_no_live_mode` | **FROZEN** | none | unfreeze |
| run_daily_shadow_scan_pipeline | `assert_dry_run_required` | **FROZEN** | none | unfreeze |
| run_remediation_shadow_only_loop | `assert_dry_run_required` | **FROZEN** | none | unfreeze |
| run_shadow_observation_experiments | `assert_no_live_mode` | **FROZEN** | none | unfreeze |
| verify_risk_release_flow | `assert_no_live_mode` | **FROZEN** | none | unfreeze |

---

## Kill-Switch Coverage

| Kill Switch | Helper | Schema | Status Report | Contract |
|---|---|---|---|---|
| QQ_NO_SUBMIT | `read_bool_env` | reflected | reflected | tested |
| QQ_NO_CANCEL | `read_bool_env` | reflected | reflected | tested |
| QQ_NO_FLATTEN | `read_bool_env` | reflected | reflected | tested |
| QQ_NO_LIVE | `read_bool_env` | reflected | reflected | tested |
| QQ_REQUIRE_DRY_RUN | `read_bool_env` | reflected | reflected | tested |

## Summary

- **Implemented**: Phase0 (complete), Phase1 (complete)
- **Tested**: ~150 tests across all components
- **Frozen**: 21 HIGH_RISK scripts (Phase3-4) — no integration until explicit unfreeze
- **Next**: Runtime integration proposal, non-frozen script audit
