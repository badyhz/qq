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

**Forbidden targets**: All 22 frozen files (21 scripts + `core/live_runner.py`), any submit/cancel/flatten chain.

**Acceptance gate**: All tests pass, no high-risk imports, readonly-only.

| Component | File | Implemented | Tested |
|---|---|---|---|
| Pure helpers | `core/execution_guards.py` | Completed | Completed (62) |
| Schema validation | `core/execution_guard_schema.py` | Completed | Completed (38) |
| Status report wrapper | `scripts/generate_execution_guard_status_report.py` | Completed | Completed (31) |
| Contract tests | `tests/unit/test_execution_guard_contract.py` | Completed | Completed (20) |

---

## Phase1 — Readonly Integration (completed)

**Scope**: CLI usage, docs, runtime integration proposal, readonly wrappers for non-frozen scripts.

**Allowed targets**:
- `scripts/generate_execution_guard_status_report.py` (extend)
- `docs/` (extend)
- New readonly scripts in `scripts/` (non-frozen)

**Forbidden targets**: All 22 frozen files (21 scripts + `core/live_runner.py`), any submit/cancel/flatten chain.

**Acceptance gate**: CLI validated, docs complete, no high-risk imports, contract tests pass.

| Target | Guard Functions | Status | Tests |
|---|---|---|---|
| CLI polish (`--compact`, `--pretty`) | `generate_report` | Completed | Completed |
| Schema drift helper | `get_guard_schema_required_keys` | Completed | Completed |
| Summary formatter | `format_guard_summary_text` | Completed | Completed |
| Report examples | JSON docs | Completed | n/a |
| Integration matrix | this file | Completed | n/a |
| Runtime integration proposal | `docs/` | Planned | n/a |

---

## Phase2 — Payload Builders (in progress)

**Scope**: Guard integration into non-frozen payload builder scripts.

**Allowed targets**:
- Non-frozen payload builder scripts (if any exist)
- Guard helper functions

**Forbidden targets**: All 22 frozen files (21 scripts + `core/live_runner.py`), any submit/cancel/flatten chain.

**Acceptance gate**: Each target has dedicated tests, all guard layers validated, no live-mode leak.

| Target | Required Guards | Status | Tests | Blocker |
|---|---|---|---|---|
| Signal trial | `assert_submit_unlocked` | Blocked | none | needs Phase1 |
| Observation shift | `assert_submit_unlocked` | Blocked | none | needs Phase1 |
| Experiment plan | `assert_dry_run_required` | Blocked | none | needs Phase1 |

---

## Phase2 Safe Integrations Completed

Non-frozen readonly/planner scripts with dry-run guard at CLI entry.

| Script | Guard | Status | Tests | Commit |
|---|---|---|---|---|
| `scripts/validate_testnet_artifacts.py` | `assert_dry_run_required` | Completed | 6 | `f4cfba0` |
| `scripts/generate_runner_dry_run_report.py` | `assert_dry_run_required` | Completed | 6 | `9ece5b1` |
| `scripts/generate_gate_decision_dashboard.py` | `assert_dry_run_required` | Completed | 6 | `8bf2181` |

---

## Phase3 — HIGH_RISK_WRITE (blocked)

**Scope**: Guard integration into frozen HIGH_RISK_WRITE scripts.

**Allowed targets**: Only after explicit unfreeze + review.

**Forbidden targets**: `core/live_runner.py`, any HIGH_RISK_RUNTIME scripts. (15 runtime files remain frozen.)

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

- **Phase0**: Completed
- **Phase1**: Completed
- **Phase2**: Blocked (waiting on Phase1 validation)
- **Phase3–4**: Frozen (22 frozen files: 21 scripts + `core/live_runner.py`)
- **Tests**: ~153 across all components
- **Next**: Runtime integration proposal, non-frozen script audit

---

## Audit Snapshot

| Field | Value |
|---|---|
| Current phase status | Phase0–1 Completed, Phase2 In Progress, Phase3–4 Frozen |
| Frozen file count | 22 (21 scripts + core/live_runner.py) |
| Phase2 safe integrations | 3 (validate_testnet_artifacts, generate_runner_dry_run_report, generate_gate_decision_dashboard) |
| execution_guard tests | ~171 |
| High-risk integration performed | No |
| Last audit | T635 Phase2 checkpoint |
