# Medium Operational Script Review Overview (T1271)

## Purpose

Define the second-wave review framework for 13 MEDIUM-risk untracked
operational scripts in the qq trading system. These scripts were not
covered by the first medium-risk review (T1171-T1180) because they
were added after initial classification.

## release_hold = HOLD

No script in this batch may be promoted, committed, or executed in
live mode until the hold is explicitly released.

## Scope

13 untracked scripts requiring review before promotion:

| Category     | Scripts                                                  |
|--------------|----------------------------------------------------------|
| OPERATIONAL  | `run_controlled_testnet_shift.py`                        |
| OPERATIONAL  | `run_daily_shadow_scan_pipeline.py`                      |
| OPERATIONAL  | `run_next_shadow_experiment_plan.py`                     |
| OPERATIONAL  | `run_observation_shift_runtime.py`                       |
| OPERATIONAL  | `run_remediation_shadow_only_loop.py`                    |
| OPERATIONAL  | `run_shadow_observation_experiments.py`                  |
| OPERATIONAL  | `run_shadow_sample_collection_pipeline.py`               |
| OPERATIONAL  | `run_shadow_universe_collector.py`                       |
| OPERATIONAL  | `run_signal_testnet_trial.py`                            |
| OPERATIONAL  | `run_spot_testnet_acceptance.py`                         |
| REPLAY       | `replay_shadow_order_plans_as_testnet_dry.py`            |
| REPLAY       | `run_replay_submit_batch.py`                             |
| SAFE_FLATTEN | `safe_flatten_testnet_symbol.py`                         |

Additionally, verification scripts exist under `scripts/verify_*`.

## Policy Documents

| Task  | Document                                | Focus              |
|-------|-----------------------------------------|--------------------|
| T1272 | Dry-run command policy                  | Command safety     |
| T1273 | Artifact write policy                   | File output rules  |
| T1274 | Import boundary policy                  | Module boundaries  |
| T1275 | Deny submit policy                      | No live orders     |
| T1276 | No credential policy                    | No secrets         |
| T1277 | No network policy                       | No live I/O        |
| T1278 | Commit isolation checklist              | Git safety         |
| T1279 | Review checklist                        | Promotion gate     |
| T1280 | Review closeout                         | Summary            |

## Invariants

- release_hold = HOLD for all documents in this set.
- No live execution, no exchange calls, no secret references.
- All scripts default to dry-run or read-only mode.
- This is a documentation-only deliverable; no code changes.
