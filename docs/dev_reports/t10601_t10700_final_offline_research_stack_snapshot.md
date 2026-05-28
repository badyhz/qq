# T10601-T10700 Final Offline Research Stack Snapshot

## 1. Current HEAD

```
4d940834b33d00895c2e411f8fee47b5e04bc65e
```

Message: `feat: offline human review workflow — T10201-T10600`

## 2. Current Tags

```
multi-strategy-research-artifact-browser-complete
multi-strategy-research-comparison-analytics-complete
multi-strategy-research-deep-hardening-complete
multi-strategy-research-human-review-complete
```

## 3. Current Known Tests

| Suite | File(s) | Count | Status |
|-------|---------|-------|--------|
| Deep Hardening | `test_deep_hardening_t9001.py` | 101 | PASS |
| Safety Regression | `test_research_safety_regression.py` | 15 | PASS |
| Artifact Browser | `test_research_artifact_browser*.py` et al. | 124 | PASS |
| Comparison | `test_research_comparison_*.py` + `test_research_bundle_series.py` + `test_research_comparison_report.py` | 84 | PASS |
| Human Review | `test_research_human_review_*.py` | 36 | PASS |
| Full Suite | all | 7248 passed, 6 skipped | PASS |

## 4. Current Known CLIs

| CLI | Status |
|-----|--------|
| Browser CLI | PASS |
| Browser comparison | PASS |
| Comparison CLI | PASS |
| Quality series CLI | PASS |
| Render report CLI | PASS |
| Review packet CLI | PASS |
| Validate review packet CLI | PASS |
| Render review report CLI | PASS |

## 5. Current Artifacts

- 30 research_quality fixture files in `tests/fixtures/research_quality/`
- All non-empty, all indexed

## 6. Current Reports

Dev reports in `docs/dev_reports/`:
- `t4201_t5200_multi_strategy_research_workbench_closeout.md`
- `t5201_t9000_research_quality_gate_closeout.md`
- `t9001_t9300_deep_hardening_gap_fix_closeout.md`
- `t9301_t9360_research_workbench_phase_closeout_snapshot.md`
- `t9301_t9360_next_backlog_reset.md`
- `t9361_t9800_offline_artifact_browser_closeout.md`
- `t9801_t10200_offline_research_comparison_analytics_closeout.md`
- `t10201_t10600_offline_human_review_workflow_closeout.md`

## 7. Current Fixture Layers

- `tests/fixtures/research_quality/` — 30 files
- Standard test fixtures in `tests/fixtures/` (if any)
- No network-dependent fixtures

## 8. Current Review Workflow

1. Generate review packet (`review packet CLI`)
2. Validate review packet (`validate review packet CLI`)
3. Render review report (`render review report CLI`)
4. Human reviews report
5. No auto-promotion

## 9. Current Comparison Workflow

1. Select artifacts for comparison
2. Run comparison CLI to compute pairwise metrics
3. Run quality series CLI for trend analysis
4. Generate comparison report
5. Render report for review

## 10. Current Artifact Browser Workflow

1. Browse available artifacts
2. Index artifacts for search
3. View artifact details
4. Compare artifacts
5. Render reports

## 11. Current Quality Gate Workflow

1. Research quality fixtures validated
2. Safety regression tests enforced
3. Quality thresholds checked
4. Results advisory only — no auto-action

## 12. Current Safety Flags

| Flag | Value |
|------|-------|
| release_hold | HOLD |
| offline only | YES |
| advisory only | YES |
| human_review_required | YES |
| live trading | NO |
| testnet submit | NO |
| exchange integration | NO |
| runtime integration | NO |
| planner integration | NO |
| network | NO |
| auto-promotion | NO |

## 13. Current Frozen/External State

Untracked live/testnet/shadow files in working tree:
```
core/live_runner.py
scripts/live_playbook.py
scripts/replay_shadow_order_plans_as_testnet_dry.py
scripts/run_controlled_testnet_shift.py
scripts/run_daily_shadow_scan_pipeline.py
scripts/run_next_shadow_experiment_plan.py
scripts/run_observation_shift_runtime.py
scripts/run_remediation_shadow_only_loop.py
scripts/run_replay_submit_batch.py
scripts/run_right_breakout_param_observation.py
scripts/run_right_breakout_scan_dry.py
scripts/run_shadow_observation_experiments.py
scripts/run_shadow_sample_collection_pipeline.py
scripts/run_shadow_universe_collector.py
scripts/run_signal_testnet_trial.py
scripts/run_spot_testnet_acceptance.py
scripts/run_testnet_order_smoke.py
scripts/safe_flatten_testnet_symbol.py
scripts/submit_approved_candidates.py
scripts/submit_replayed_testnet_payload.py
scripts/verify_risk_release_flow.py
scripts/verify_testnet_repair_scenarios.py
research/
```

These are external state. Not staged. Not imported. Not executed.

## 14. Recovery Instructions

To restore to this snapshot state:
```bash
git checkout 4d940834b33d00895c2e411f8fee47b5e04bc65e
```

To verify full suite:
```bash
PYTHONPATH=. .venv/bin/pytest -q
```

Expected: 7248 passed, 6 skipped, 0 failed.

## 15. How To Re-run Offline Stack

```bash
# Full suite
PYTHONPATH=. .venv/bin/pytest -q

# Human review tests
PYTHONPATH=. .venv/bin/pytest -q tests/unit/test_research_human_review_*.py

# Comparison tests
PYTHONPATH=. .venv/bin/pytest -q tests/unit/test_research_comparison_*.py tests/unit/test_research_bundle_series.py tests/unit/test_research_comparison_report.py

# Artifact browser tests
PYTHONPATH=. .venv/bin/pytest -q tests/unit/test_research_artifact_browser*.py tests/unit/test_research_artifact_index*.py tests/unit/test_research_report_view_model*.py tests/unit/test_research_static_report_renderer*.py

# Deep hardening tests
PYTHONPATH=. .venv/bin/pytest -q tests/unit/test_deep_hardening_t9001.py tests/unit/test_research_safety_regression.py

# Fixture count check
find tests/fixtures/research_quality -type f ! -name ".gitkeep" | wc -l
# Expected: 30
```

## 16. How To Start Next Window

1. Read `docs/dev_reports/t10601_t10700_next_phase_options.md`
2. Choose next phase (recommend T10701-T11000 or T10701-T11200)
3. Create task range and PRD
4. Do NOT activate live/testnet/runtime
5. Do NOT modify safety flags
6. Do NOT touch untracked external files
