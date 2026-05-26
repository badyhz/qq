# Execution Guard Integration Matrix

## Phase0 — Helper / Schema / Contract (completed)

| Component | File | Implemented | Tested | Next Phase |
|---|---|---|---|---|
| Pure helpers | `core/execution_guards.py` | yes | yes (62 tests) | Phase1 readonly integration |
| Schema validation | `core/execution_guard_schema.py` | yes | yes (30 tests) | Phase1 schema consumer |
| Status report wrapper | `scripts/generate_execution_guard_status_report.py` | yes | yes (21 tests) | Phase1 CLI usage |
| Contract tests | `tests/unit/test_execution_guard_contract.py` | yes | yes (14 tests) | Phase1 cross-module |

## Phase1 — Readonly Integration (planned)

| Target | Guard Functions | Status | Tests | Next |
|---|---|---|---|---|
| Report generation | `build_execution_guard_report` | done | done | docs examples |
| Schema validation | `validate_guard_report` | done | done | CLI integration |
| Summary helper | `build_guard_report_summary` | done | done | runtime integration |

## Phase2 — Payload Builders (blocked)

| Target | Required Guards | Status | Tests | Blocker |
|---|---|---|---|---|
| Signal trial | `assert_submit_unlocked` | not started | none | needs Phase1 |
| Observation shift | `assert_submit_unlocked` | not started | none | needs Phase1 |
| Experiment plan | `assert_dry_run_required` | not started | none | needs Phase1 |

## Phase3 — HIGH_RISK_WRITE (blocked)

| Target | Required Guards | Status | Tests | Blocker |
|---|---|---|---|---|
| submit_approved_candidates | `assert_submit_unlocked` | not started | none | needs Phase2 |
| submit_replayed_testnet_payload | `assert_submit_unlocked` | not started | none | needs Phase2 |
| run_replay_submit_batch | `assert_submit_unlocked` | not started | none | needs Phase2 |
| safe_flatten_testnet_symbol | `assert_flatten_unlocked` | not started | none | needs Phase2 |
| run_spot_testnet_acceptance | `assert_submit_unlocked` | not started | none | needs Phase2 |
| run_testnet_order_smoke | `assert_submit_unlocked` | not started | none | needs Phase2 |
| verify_testnet_repair_scenarios | `assert_cancel_unlocked` | not started | none | needs Phase2 |

## Phase4 — HIGH_RISK_RUNTIME (blocked)

| Target | Required Guards | Status | Tests | Blocker |
|---|---|---|---|---|
| live_runner.py | all T601+T602 | not started | none | needs Phase3 |
| live_playbook.py | all T601+T602 | not started | none | needs Phase3 |
| run_controlled_testnet_shift | `assert_no_live_mode` | not started | none | needs Phase3 |
| run_daily_shadow_scan_pipeline | `assert_dry_run_required` | not started | none | needs Phase3 |
| run_remediation_shadow_only_loop | `assert_dry_run_required` | not started | none | needs Phase3 |
| run_shadow_observation_experiments | `assert_no_live_mode` | not started | none | needs Phase3 |
| verify_risk_release_flow | `assert_no_live_mode` | not started | none | needs Phase3 |

## Kill-Switch Coverage

| Kill Switch | Helper | Schema | Status Report | Contract |
|---|---|---|---|---|
| QQ_NO_SUBMIT | `read_bool_env` | reflected | reflected | tested |
| QQ_NO_CANCEL | `read_bool_env` | reflected | reflected | tested |
| QQ_NO_FLATTEN | `read_bool_env` | reflected | reflected | tested |
| QQ_NO_LIVE | `read_bool_env` | reflected | reflected | tested |
| QQ_REQUIRE_DRY_RUN | `read_bool_env` | reflected | reflected | tested |

## Summary

- **Implemented**: 4 components (helpers, schema, status report, contract tests)
- **Tested**: 127 tests total across all components
- **Blocked**: Phase2-4 frozen scripts — no integration until Phase1 validated
- **Next**: CLI usage docs, runtime integration proposal
