# Remaining High-Risk Frozen Inventory

**Frozen count**: 22 files (21 scripts + 1 core module)

Last updated: 2026-05-26

---

## HIGH_RISK_WRITE (7 scripts)

| # | File | Risk |
|---|---|---|
| 1 | `scripts/submit_approved_candidates.py` | Order submission |
| 2 | `scripts/submit_replayed_testnet_payload.py` | Order submission |
| 3 | `scripts/run_replay_submit_batch.py` | Batch order submission |
| 4 | `scripts/safe_flatten_testnet_symbol.py` | Position flatten |
| 5 | `scripts/run_spot_testnet_acceptance.py` | Spot order acceptance |
| 6 | `scripts/run_testnet_order_smoke.py` | Testnet order smoke test |
| 7 | `scripts/verify_testnet_repair_scenarios.py` | Testnet repair verification |

## HIGH_RISK_RUNTIME (15 files)

| # | File | Risk |
|---|---|---|
| 1 | `core/live_runner.py` | Core runtime loop |
| 2 | `scripts/live_playbook.py` | Live trading playbook |
| 3 | `scripts/replay_shadow_order_plans_as_testnet_dry.py` | Shadow order replay |
| 4 | `scripts/run_controlled_testnet_shift.py` | Controlled testnet shift |
| 5 | `scripts/run_daily_shadow_scan_pipeline.py` | Daily shadow scan |
| 6 | `scripts/run_next_shadow_experiment_plan.py` | Shadow experiment planner |
| 7 | `scripts/run_observation_shift_runtime.py` | Observation shift runtime |
| 8 | `scripts/run_remediation_shadow_only_loop.py` | Remediation shadow loop |
| 9 | `scripts/run_replay_submit_batch.py` | Replay submit batch (runtime) |
| 10 | `scripts/run_right_breakout_param_observation.py` | Right breakout param observation |
| 11 | `scripts/run_right_breakout_scan_dry.py` | Right breakout scan dry |
| 12 | `scripts/run_shadow_observation_experiments.py` | Shadow observation experiments |
| 13 | `scripts/run_shadow_sample_collection_pipeline.py` | Shadow sample collection |
| 14 | `scripts/run_shadow_universe_collector.py` | Shadow universe collector |
| 15 | `scripts/run_signal_testnet_trial.py` | Signal testnet trial |

---

## Policy

- **Visible untracked on purpose**: These files are intentionally left as untracked `??` in git status.
- **Do not gitignore**: They must remain visible so reviewers can see what frozen code exists.
- **Do not commit until explicit unfreeze**: No commits involving these files without deliberate unfreeze + review.
- **Readonly audits only**: Allowed actions on frozen files are limited to:
  - Read-only audits
  - Helper extraction proposals (docs)
  - Guard integration proposals (docs)
- **No code changes**: Do not modify, refactor, or patch any frozen file.
