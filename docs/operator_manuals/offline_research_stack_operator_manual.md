# Offline Research Stack Operator Manual

## 1. System Overview

The offline research stack is a complete offline-only quantitative research operating system. It provides deterministic, reproducible, advisory-only research capabilities for multi-strategy backtesting, quality gating, artifact browsing, comparison analytics, and human review workflows.

**Key properties:**
- Offline only. No network. No exchange.
- Advisory only. No live trading. No testnet submission.
- release_hold = HOLD
- Human review required for all outputs
- No auto-promotion (no_auto_promotion) mechanism

## 2. Phase History

| Phase | Task Range | Description |
|-------|-----------|-------------|
| Multi-Strategy Research Workbench | T4201-T5200 | Core research infrastructure |
| Deep Hardening | T5201-T9000 | Quality gates, fixtures, regression |
| Deep Hardening Gap Fix | T9001-T9300 | Gap fixes |
| Phase Closeout | T9301-T9360 | Closeout and backlog reset |
| Artifact Browser / Report UX | T9361-T9800 | Browser, index, renderer |
| Comparison Analytics | T9801-T10200 | Comparison, series, scorecard |
| Human Review Workflow | T10201-T10600 | Review packet, validate, render |
| Final Snapshot | T10601-T10700 | Documentation/snapshot/audit |
| Operator Manual / Experiment Library / Governance | T10701-T13000 | Operator docs, experiment library, governance |

## 3. Current Tags

| Tag | Description |
|-----|-------------|
| `multi-strategy-research-deep-hardening-complete` | Deep hardening phase complete |
| `multi-strategy-research-artifact-browser-complete` | Artifact browser complete |
| `multi-strategy-research-comparison-analytics-complete` | Comparison analytics complete |
| `multi-strategy-research-human-review-complete` | Human review workflow complete |

## 4. Current Commands

### Validate Experiment Library
```bash
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/offline_research_experiment_library_validation \
  --strict --release-hold HOLD
```

### Validate Docs Governance
```bash
python3 scripts/validate_offline_research_stack_docs.py \
  --docs-root docs \
  --output-dir /tmp/offline_research_governance_validation \
  --strict --release-hold HOLD
```

### Build Operator Bundle
```bash
python3 scripts/build_offline_research_operator_bundle.py \
  --docs-root docs \
  --experiment-catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/offline_research_operator_bundle \
  --strict --release-hold HOLD
```

### Run Full Test Suite
```bash
PYTHONPATH=. .venv/bin/pytest -q
```

### Run Offline Research Workbench
```bash
python3 scripts/run_multi_strategy_research_workbench.py \
  --fixture-dir tests/fixtures/historical_backtest_lab \
  --output-dir /tmp/multi_strategy_research_workbench \
  --strategies breakout,mean_reversion,momentum,volatility_compression \
  --symbols BTCUSDT,ETHUSDT --timeframes 5m,15m \
  --split-mode rolling --search-budget 120 --chunk-size 25
```

### Run Quality Gate
```bash
python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --deterministic-seed 424242 --strict --release-hold HOLD
```

### Build Artifact Browser
```bash
python3 scripts/build_research_artifact_browser.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --output-dir /tmp/research_artifact_browser \
  --strict --release-hold HOLD
```

### Build Comparison Analytics
```bash
python3 scripts/build_research_comparison_analytics.py \
  --bundle baseline=/tmp/research_artifact_browser \
  --bundle candidate=/tmp/research_artifact_browser \
  --output-dir /tmp/research_comparison_analytics \
  --strict --release-hold HOLD
```

### Build Human Review Packet
```bash
python3 scripts/build_research_human_review_packet.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --artifact-browser-dir /tmp/research_artifact_browser \
  --comparison-dir /tmp/research_comparison_analytics \
  --output-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

### Validate Human Review Packet
```bash
python3 scripts/validate_research_human_review_packet.py \
  --review-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

## 5. Artifact Map

| Artifact | Source | Description |
|----------|--------|-------------|
| `workbench_results.json` | Workbench | Raw backtest results |
| `quality_gate.json` | Quality Gate | Quality validation results |
| `manifest.json` | Quality Gate | Quality manifest with safety flags |
| `artifact_browser/` | Artifact Browser | Indexed artifact collection |
| `comparison_report.json` | Comparison | Pairwise comparison results |
| `quality_series.json` | Comparison | Quality series data |
| `scorecard.json` | Comparison | Strategy scorecard |
| `review_packet.json` | Human Review | Complete review packet |
| `review_checklist.json` | Human Review | Human review checklist |
| `review_signoff_template.json` | Human Review | Signoff template |
| `review_audit_trail.json` | Human Review | Audit trail |
| `governance_validation.json` | Governance | Governance validation |
| `experiment_library_validation.json` | Experiment Library | Library validation |
| `operator_bundle_index.json` | Operator Bundle | Bundle index |

## 6. Report Map

| Report | Format | Description |
|--------|--------|-------------|
| Quality Report | MD/HTML | Quality gate results |
| Artifact Browser | HTML | Standalone artifact browser |
| Comparison Report | MD | Pairwise comparison analysis |
| Human Review Report | MD/HTML | Full review report |
| Governance Validation | MD | Governance validation results |
| Operator Bundle | MD/HTML | Complete operator bundle |

## 7. Fixture Map

| Fixture Area | Contents |
|-------------|----------|
| `tests/fixtures/historical_backtest_lab/` | Historical OHLCV data |
| `tests/fixtures/research_quality/` | Quality gate fixtures |
| `tests/fixtures/research_human_review/` | Review workflow fixtures |
| `tests/fixtures/offline_research_experiment_library/` | Experiment catalog and definitions |
| `tests/fixtures/multi_strategy_research/` | Multi-strategy fixtures |

## 8. Safety Boundary

**release_hold = HOLD** (immutable without explicit human approval)

Safety flags (all must be true):
- `no_live = true`
- `no_submit = true`
- `no_exchange = true`
- `no_network = true`
- `no_runtime_integration = true`
- `no_planner_integration = true`
- `advisory_only = true`
- `human_review_required = true`

Forbidden actions:
- Live trading
- Testnet submission
- Order placement/cancellation/flattening
- Runtime integration
- Planner integration
- Auto-promotion
- Network calls
- Exchange client usage

## 9. Known Untracked External-State Warning

The following untracked files exist in the working tree. They are external state (live/testnet/shadow related). Do NOT stage, import, execute, or modify them:

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
research/ (untracked directory)
```

## 10. How to Run Full Offline Pipeline

1. Run workbench: `python3 scripts/run_multi_strategy_research_workbench.py ...`
2. Run quality gate: `python3 scripts/run_multi_strategy_research_quality_gate.py ...`
3. Build artifact browser: `python3 scripts/build_research_artifact_browser.py ...`
4. Build comparison: `python3 scripts/build_research_comparison_analytics.py ...`
5. Build review packet: `python3 scripts/build_research_human_review_packet.py ...`
6. Validate review packet: `python3 scripts/validate_research_human_review_packet.py ...`

## 11. How to Inspect Output

- JSON artifacts: `cat /tmp/<output_dir>/<artifact>.json | python3 -m json.tool`
- HTML reports: Open in browser (offline)
- MD reports: View in any text editor
- Logs: Check `/tmp/<output_dir>/` for all generated files

## 12. How to Compare Bundles

```bash
python3 scripts/build_research_comparison_analytics.py \
  --bundle baseline=/tmp/research_artifact_browser \
  --bundle candidate=/tmp/new_artifact_browser \
  --output-dir /tmp/research_comparison_analytics \
  --strict --release-hold HOLD
```

## 13. How to Build Human Review Packet

```bash
python3 scripts/build_research_human_review_packet.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --artifact-browser-dir /tmp/research_artifact_browser \
  --comparison-dir /tmp/research_comparison_analytics \
  --output-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

## 14. How to Validate Signoff

```bash
python3 scripts/validate_research_human_review_packet.py \
  --review-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

Allowed signoff decisions:
- REJECT
- REQUEST_MORE_RESEARCH
- ACCEPT_ADVISORY_RESEARCH_ONLY

Forbidden signoff decisions (never use):
- APPROVE_LIVE (forbidden)
- APPROVE_TESTNET_SUBMIT (forbidden)
- APPROVE_RUNTIME (forbidden)
- APPROVE_PLANNER_INTEGRATION (forbidden)
- AUTO_PROMOTE (forbidden)

## 15. How to Recover from Missing Artifacts

See `docs/recovery/missing_quality_artifacts_recovery.md`.

Steps:
1. Identify which artifact is missing
2. Check if source data exists
3. Re-run the pipeline stage that generates the artifact
4. Verify artifact was generated
5. Re-run downstream stages

## 16. How to Handle Corrupted JSON

See `docs/recovery/corrupted_json_recovery.md`.

Steps:
1. Identify corrupted file
2. Check if backup exists in git history
3. Re-generate from source stage
4. Validate JSON syntax
5. Re-run downstream stages

## 17. How to Handle Failed Quality Gate

Steps:
1. Check quality gate output for specific failures
2. Review quality metrics against thresholds
3. Determine if failure is data quality issue or threshold issue
4. Re-run with adjusted parameters or fix data
5. See `docs/runbooks/run_quality_gate_only.md`

## 18. How to Handle Deterministic Mismatch

See `docs/recovery/reproducibility_mismatch_recovery.md`.

Steps:
1. Verify same deterministic seed was used
2. Check for fixture data changes
3. Check for code changes between runs
4. Re-run with same parameters
5. If persistent, investigate root cause

## 19. What Not to Do

- Do NOT use `git add .`
- Do NOT stage untracked live/testnet/shadow files
- Do NOT change release_hold from HOLD without human approval
- Do NOT enable live trading
- Do NOT submit orders (live or testnet)
- Do NOT integrate with runtime/planner
- Do NOT auto-promote research results
- Do NOT use network calls in offline modules
- Do NOT import exchange clients
- Do NOT skip human review

## 20. Next Safe Extension Rules

Safe extensions must:
- Be offline only
- Be advisory only
- Maintain release_hold = HOLD
- Require human review
- Not integrate with live/testnet/runtime/planner
- Not auto-promote
- Pass governance validation
- Pass full test suite

Safe extension areas:
- More offline experiment fixtures
- Offline report UX polish
- Offline research result cataloging
- Documentation maintenance
- Additional quality metrics
- Additional comparison analytics
