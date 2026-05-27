# Multi-Strategy Research Workbench Deep Hardening 10h PRD

## 1. Executive Summary

This PRD defines the T5201-T9000 Multi-Strategy Research Workbench Deep Hardening Program. It is an offline-only, evidence-driven hardening wave for the completed T4201-T5200 workbench.

The previous wave proved that the offline multi-strategy research bundle can run. This wave upgrades the system so that research output is reproducible, stress-tested, leakage-checked, robustness-scored, adversarially validated, and blocked from promotion unless evidence is strong.

This is PRD authoring only. The implementation wave described here must not start until a future execution agent is explicitly instructed to execute T5201-T9000.

The future executor must not collapse this into a minimal scaffold. A schema-only phase is incomplete. A phase only creates a dataclass without tests, negative cases, fixtures, and artifact output is incomplete.

## 2. Current System State

Known completed workbench commits:

- `fb19a06 docs: add multi-strategy research workbench PRD`
- `1506492 feat: multi-strategy research workbench — T4201-T5200`
- `eb3fa13 fix: write reports before manifest build to fix artifact indexing`
- `a7024b5 fix: add root conftest to run @pytest.mark.anyio tests via asyncio.run()`
- `fbee716 docs: close out multi-strategy research workbench`

Verified state:

- Workbench acceptance command passed.
- Required artifacts exist.
- Full unit suite passed:
  - `6533 passed`
  - `6 skipped`
  - `0 failed`
- Safety flags:
  - `release_hold=HOLD`
  - `no_live=True`
  - `no_submit=True`
  - `no_exchange=True`
  - `no_runtime_integration=True`
  - `no_planner_integration=True`
  - `no_network=True`
- T5201+ status: `HUMAN_REVIEW_REQUIRED`.

Read first before implementation:

- `docs/dev_prd/multi_strategy_research_workbench_prd.md`
- `docs/dev_reports/t4201_t5200_multi_strategy_research_workbench_closeout.md`
- T4201-T5200 added modules only as needed.

## 3. Why This Is a 10-Hour Hardening Program

This cannot be a one-hour skeleton because it requires:

- Multiple independent validation passes.
- Multiple fixture classes.
- Deterministic reproducibility checks.
- Artifact hash comparison.
- Negative controls.
- Adversarial fixtures.
- Bootstrap / Monte Carlo style resampling.
- Parameter perturbation grids.
- Split leakage checks.
- Report quality checks.
- Safety regression checks.
- Closeout evidence generation.
- Full suite verification.

Size target:

- Task range: T5201-T9000.
- 80-120 phases.
- 70-120 expected changed/added files.
- 800-1500 unit/acceptance assertions.
- Multiple CLIs.
- Multiple fixture directories.
- Multiple generated reports.
- Full closeout doc.
- Final acceptance bundle.

Executor anti-collapse rule:

- If a phase only creates a schema/dataclass without tests, negative cases, fixtures, and artifact output, it is incomplete.
- Every major feature must have:
  - normal test
  - edge case test
  - adversarial/negative test
  - deterministic output test
  - artifact shape test
  - safety boundary test where applicable

## 4. Product Goal

Upgrade the Multi-Strategy Research Workbench from:

> offline multi-strategy bundle can run

to:

> research output is reproducible, stress-tested, leakage-checked, robustness-scored, adversarially validated, and blocked from promotion unless evidence is strong.

The output remains advisory research only. It must not trigger live trading, testnet submission, runtime scheduling, planner promotion, exchange interaction, cancellation, flattening, or any order placement.

## 5. Non-goals

This wave does not:

- Implement live trading.
- Implement testnet submission.
- Submit orders.
- Cancel orders.
- Flatten positions.
- Connect to Binance.
- Connect to any exchange client.
- Add network calls.
- Integrate with runtime.
- Integrate with planner.
- Auto-promote strategies.
- Modify frozen backlog files.
- Read or embed secrets, credentials, API keys, or account data.
- Load full CSV/JSONL/log files into agent context.

## 6. Safety Boundary

Hard safety rules:

- Offline only.
- No network.
- No Binance.
- No exchange client.
- No testnet submit.
- No live trading.
- No order placement.
- No cancel.
- No flatten.
- No submit.
- No runtime integration.
- No planner integration.
- No secrets / credentials / API keys.
- `release_hold` must remain `HOLD`.
- T5201+ remains `HUMAN_REVIEW_REQUIRED`.
- Research output is advisory only.
- No auto-promotion to live/testnet/runtime.
- No modification of frozen backlog files.
- No `git add .`.
- Explicit `git add` only.
- Do not load full CSV/JSONL/log files into context; use chunked/head/tail/rg summaries.

Safety invariants required in every manifest:

- `release_hold=HOLD`
- `no_live=True`
- `no_submit=True`
- `no_exchange=True`
- `no_runtime_integration=True`
- `no_planner_integration=True`
- `no_network=True`
- `advisory_only=True`
- `human_review_required=True`

## 7. Frozen / Forbidden Files

The working tree may contain pre-existing untracked files, including frozen filenames. Treat them as pre-existing external state.

The executor must not:

- Stage them.
- Modify them.
- Delete them.
- Rename them.
- Format them.
- Import them.
- Execute them.
- Use them as fixtures unless explicitly listed in this PRD.
- Use `git add .`.

Frozen-file status must be checked at the end of every milestone. If any frozen file is touched, the milestone fails. If any frozen file is staged, the wave fails.

## 8. Allowed Areas

Expected implementation file areas:

- `core/research_quality_*.py`
- `core/data_quality_deep_audit*.py`
- `core/split_leakage_*.py`
- `core/oos_validation_*.py`
- `core/parameter_robustness_*.py`
- `core/strategy_robustness_*.py`
- `core/portfolio_robustness_*.py`
- `core/negative_control_*.py`
- `core/bootstrap_research_*.py`
- `core/regime_research_*.py`
- `core/report_quality_*.py`
- `core/research_reproducibility_*.py`
- `core/research_quality_manifest*.py`
- `core/research_quality_bundle*.py`
- `core/research_quality_closeout*.py`
- `scripts/run_multi_strategy_research_quality_gate.py`
- `scripts/run_strategy_robustness_lab.py`
- `scripts/run_parameter_robustness_lab.py`
- `scripts/run_portfolio_robustness_lab.py`
- `scripts/run_negative_control_lab.py`
- `scripts/run_bootstrap_research_lab.py`
- `scripts/run_regime_research_lab.py`
- `scripts/compare_research_quality_bundles.py`
- `scripts/build_research_quality_bundle.py`
- `scripts/generate_research_quality_closeout.py`
- `tests/unit/test_research_quality_*.py`
- `tests/unit/test_data_quality_deep_audit*.py`
- `tests/unit/test_split_leakage_*.py`
- `tests/unit/test_oos_validation_*.py`
- `tests/unit/test_parameter_robustness_*.py`
- `tests/unit/test_strategy_robustness_*.py`
- `tests/unit/test_portfolio_robustness_*.py`
- `tests/unit/test_negative_control_*.py`
- `tests/unit/test_bootstrap_research_*.py`
- `tests/unit/test_regime_research_*.py`
- `tests/unit/test_report_quality_*.py`
- `tests/unit/test_research_reproducibility_*.py`
- `tests/fixtures/research_quality/base/*`
- `tests/fixtures/research_quality/adversarial/*`
- `tests/fixtures/research_quality/negative_control/*`
- `tests/fixtures/research_quality/regime/*`
- `tests/fixtures/research_quality/bootstrap/*`
- `tests/fixtures/research_quality/expected/*`
- `docs/dev_reports/t5201_t9000_research_quality_gate_closeout.md`

## 9. User Stories

1. As a research operator, I want the workbench to reject weak strategy bundles before they can be interpreted as actionable.
2. As a reviewer, I want every score to link to evidence artifacts and reason-coded warnings.
3. As a safety reviewer, I want proof that no runtime, planner, exchange, submit, cancel, flatten, network, or secret path was touched.
4. As a quant researcher, I want data quality failures, split leakage, and OOS instability to block promotion.
5. As a quant researcher, I want negative controls to prove that real strategies beat random/shuffled/permuted/inverted baselines.
6. As a quant researcher, I want bootstrap confidence intervals and worst-case percentiles before trusting performance.
7. As a reviewer, I want rerun reproducibility and artifact hashes to prove deterministic output.
8. As a future implementer, I want a phase plan large enough to prevent shallow schema-only work.

## 10. Functional Requirements

FR-1: The quality gate must build a complete quality bundle from an existing workbench output directory.

FR-2: The quality gate must produce required artifacts listed in Section 25.

FR-3: The quality gate must compute composite quality score, evidence completeness score, hard block reasons, advisory-only promotion status, confidence bands, and final PASS/PARTIAL/FAIL.

FR-4: The quality gate must fail strict mode if required evidence is missing.

FR-5: The quality gate must fail strict mode if data quality audit finds hard failures.

FR-6: The quality gate must fail strict mode if split leakage is detected.

FR-7: The quality gate must fail strict mode if OOS split count is below `--min-oos-splits`.

FR-8: The quality gate must fail strict mode if parameter fragility exceeds `--max-parameter-fragility`.

FR-9: The quality gate must fail strict mode if portfolio overlap risk exceeds `--max-overlap-risk`.

FR-10: The quality gate must fail strict mode if negative control margin is below `--min-negative-control-margin`.

FR-11: The quality gate must fail strict mode if bootstrap or regime breakdown is required but absent.

FR-12: Reproducibility must compare two quality bundles and require identical hashes except allowlisted generated timestamp fields.

FR-13: Reports must include human-readable warnings, artifact links, and metric consistency checks.

FR-14: Safety regression must prove `release_hold=HOLD` and all no-live/no-submit/no-exchange/no-runtime/no-planner/no-network flags.

FR-15: No phase can be complete without tests, negative/adversarial cases, deterministic output checks, artifact shape checks, and safety checks where applicable.

## 11. Data Quality Deep Audit

Program B must detect and report:

- Missing bars.
- Duplicate bars.
- Non-monotonic timestamps.
- Zero volume.
- Impossible OHLC.
- Empty or NaN metrics.
- Stale symbol/timeframe coverage.
- Inconsistent split coverage.
- Fixture corruption.
- Header/schema mismatch.
- Partial coverage.
- Insufficient coverage.

Required artifact:

- `data_quality_deep_audit.json`

Required behavior:

- Every finding has severity, reason code, affected symbol/timeframe/split, count, and block status.
- Hard data corruption blocks promotion.
- Sparse data can produce warning or block depending on severity.
- The audit never fetches missing data from network.

## 12. Split / Leakage / OOS Validation

Program C must validate:

- Rolling split verification.
- Anchored split verification.
- Chronological ordering.
- No train/test overlap.
- Split boundary hash.
- Leakage score.
- OOS stability by split.
- Rejected split reasons.

Required artifacts:

- `split_leakage_report.json`
- `oos_validation_report.json`

Required behavior:

- Any overlap between train/test blocks promotion.
- Non-chronological split ordering blocks promotion.
- Boundary hashes must be deterministic.
- Rejected splits must include human-readable reasons.
- OOS instability is scored by split, strategy, symbol, timeframe, and portfolio level.

## 13. Parameter Robustness Lab

Program D must implement:

- Neighborhood perturbation.
- Fragility score.
- Overfit suspicion score.
- Parameter heatmap data.
- Top-N stability.
- Dominance stability.
- Search budget enforcement.
- Sensitivity ranking.

Required artifacts:

- `parameter_stability.json`
- `parameter_fragility_report.json`
- `parameter_sensitivity_ranking.json`

Required behavior:

- Fragility above threshold blocks promotion.
- Needle-in-haystack parameter peaks raise overfit suspicion.
- Search budget overflow fails strict mode.
- Ranking must be deterministic.

## 14. Strategy Robustness Lab

Program E must implement:

- Strategy-by-strategy stress test.
- Regime sensitivity.
- Symbol sensitivity.
- Timeframe sensitivity.
- Entry/exit behavior diagnostics.
- Sparse-signal handling.
- Noisy fixture handling.
- Adverse fixture handling.

Required artifact:

- `strategy_robustness_report.json`

Required behavior:

- Sparse signal evidence cannot produce false confidence.
- Adverse fixtures must detect degradation.
- Entry/exit diagnostics must never imply order placement.
- Strategy failures produce reason-coded warnings or blocks.

## 15. Portfolio Robustness Lab

Program F must implement:

- Correlation proxy.
- Overlap score.
- Crowding score.
- Same-bar collision analysis.
- Exposure concentration.
- Strategy contribution stability.
- Portfolio degradation test.
- Portfolio drawdown proxy.

Required artifacts:

- `portfolio_robustness_report.json`
- `portfolio_overlap_risk.json`
- `correlation_proxy_report.json`

Required behavior:

- High overlap risk above threshold blocks promotion.
- Strategy contribution dominated by one fragile strategy blocks promotion.
- Portfolio drawdown proxy degradation must appear in report.
- Same-bar collision analysis must not trigger live order logic.

## 16. Negative Controls

Program G must implement:

- Random strategy baseline.
- Shuffled returns baseline.
- Permuted signal baseline.
- Inverted signal baseline.
- Random parameter baseline.
- Negative controls must underperform.
- Fail if real strategy cannot beat controls.

Required artifacts:

- `negative_control_report.json`
- `random_strategy_baseline.json`
- `shuffled_returns_baseline.json`
- `inverted_signal_baseline.json`

Recommended optional artifact:

- `permuted_signal_baseline.json`
- `random_parameter_baseline.json`

Required behavior:

- Negative control margin below threshold blocks promotion.
- Controls must be deterministic with seed.
- Controls must not use network or exchange data.

## 17. Bootstrap / Monte Carlo / Resampling

Program H must implement:

- Deterministic bootstrap with seed.
- Confidence intervals.
- Win-rate uncertainty.
- Expectancy uncertainty.
- Stability under resampling.
- Worst-case percentile.
- Reproducible resample artifacts.

Required artifacts:

- `bootstrap_report.json`
- `bootstrap_confidence_intervals.json`

Required behavior:

- Same seed and same input produce identical resample artifacts.
- Worst-case percentile below safety threshold blocks promotion.
- Missing bootstrap when `--require-bootstrap` is set fails strict mode.
- Confidence intervals must appear in promotion gate and quality summary.

## 18. Regime Segmentation

Program I must implement:

- Trend / chop / volatility buckets.
- BTC proxy regime compatibility.
- Per-regime scorecard.
- Regime failure detection.
- Regime concentration warning.
- Regime-aware promotion block.

Required artifacts:

- `regime_breakdown.json`
- `regime_failure_report.json`

Required behavior:

- Regime concentration warning appears when performance comes from one narrow regime.
- Regime failure blocks promotion if required by strict mode.
- BTC proxy compatibility must use existing offline artifacts only.

## 19. Report Quality Gate

Program J must implement:

- Report completeness checker.
- Required sections.
- Metric consistency checks.
- Artifact cross-link validation.
- Empty/NaN metric detection.
- Human-readable warnings.
- HTML report generated.
- Markdown report generated.

Required artifacts:

- `report_quality_check.json`
- `report.md`
- `report.html`

Required behavior:

- Reports must include advisory-only language.
- Reports must link required artifacts.
- Reports must not include external network assets.
- Metric mismatches between summary and detailed artifacts fail strict mode.
- Empty/NaN critical metrics fail strict mode.

## 20. Promotion Gate v2

Program A must implement Research Quality Gate v2:

- Composite quality score.
- Required evidence checklist.
- Advisory-only promotion status.
- Hard block reasons.
- Confidence bands.
- Evidence completeness scoring.

Required artifacts:

- `quality_gate_summary.json`
- `robustness_scorecard.json`
- `promotion_gate_v2.json`

Required behavior:

- Promotion is advisory-only.
- There is no live/testnet/runtime/planner promotion.
- `release_hold=HOLD` is mandatory.
- `human_review_required=True` is mandatory.
- Hard blocks override composite score.

## 21. Reproducibility / Determinism

Program K must implement:

- Deterministic seed control.
- Artifact hashing.
- Input hash capture.
- Output hash capture.
- Rerun diff detector.
- Reproducibility manifest.
- Deterministic report ordering.
- Stable JSON formatting.

Required artifacts:

- `reproducibility_manifest.json`
- `rerun_diff_report.json`
- `manifest.json`

Required behavior:

- Same input + same seed = identical output hashes except allowlisted timestamp fields.
- JSON formatting is stable.
- Lists and reports sort deterministically.
- Hashes include required input and output artifacts.
- The comparator must fail unexpected diffs.

## 22. Artifact Hashing / Bundle Comparison

The bundle comparator must support:

```bash
python3 scripts/compare_research_quality_bundles.py \
  --left /tmp/multi_strategy_research_quality_gate \
  --right /tmp/multi_strategy_research_quality_gate_rerun \
  --require-identical-hashes \
  --allow-timestamp-fields generated_at
```

Required behavior:

- Reads only bundle artifacts.
- Compares required artifact inventory.
- Compares input and output hashes.
- Ignores only explicitly allowlisted timestamp fields.
- Fails if any required artifact is missing.
- Fails if any non-allowlisted artifact hash differs.

## 23. Safety Regression

Program M must verify:

- `release_hold` stays `HOLD`.
- `advisory_only` stays `true`.
- `human_review_required` stays `true`.
- No submit/network/exchange/runtime/planner imports.
- Frozen file guard.
- Dirty workspace guard.
- No `git add .` evidence.
- Artifacts prove no live/testnet escalation.

Safety regression must be executed in targeted tests and final acceptance.

## 24. CLI Specification

### 24.1 Full Quality Gate CLI

```bash
python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --min-oos-splits 3 \
  --min-stability-score 0.60 \
  --max-parameter-fragility 0.40 \
  --max-overlap-risk 0.70 \
  --min-negative-control-margin 0.10 \
  --bootstrap-iterations 200 \
  --deterministic-seed 424242 \
  --require-negative-control \
  --require-regime-breakdown \
  --require-bootstrap \
  --require-reproducibility \
  --strict \
  --release-hold HOLD
```

Must write all required quality gate artifacts or fail nonzero.

### 24.2 Strategy Robustness CLI

```bash
python3 scripts/run_strategy_robustness_lab.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --deterministic-seed 424242 \
  --strict
```

### 24.3 Parameter Robustness CLI

```bash
python3 scripts/run_parameter_robustness_lab.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --search-budget 120 \
  --deterministic-seed 424242 \
  --strict
```

### 24.4 Portfolio Robustness CLI

```bash
python3 scripts/run_portfolio_robustness_lab.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --max-overlap-risk 0.70 \
  --deterministic-seed 424242 \
  --strict
```

### 24.5 Negative Control CLI

```bash
python3 scripts/run_negative_control_lab.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --min-negative-control-margin 0.10 \
  --deterministic-seed 424242 \
  --strict
```

### 24.6 Bootstrap CLI

```bash
python3 scripts/run_bootstrap_research_lab.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --bootstrap-iterations 200 \
  --deterministic-seed 424242 \
  --strict
```

### 24.7 Regime CLI

```bash
python3 scripts/run_regime_research_lab.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --deterministic-seed 424242 \
  --strict
```

### 24.8 Bundle Build CLI

```bash
python3 scripts/build_research_quality_bundle.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --strict \
  --release-hold HOLD
```

### 24.9 Bundle Compare CLI

```bash
python3 scripts/compare_research_quality_bundles.py \
  --left /tmp/multi_strategy_research_quality_gate \
  --right /tmp/multi_strategy_research_quality_gate_rerun \
  --require-identical-hashes \
  --allow-timestamp-fields generated_at
```

### 24.10 Closeout CLI

```bash
python3 scripts/generate_research_quality_closeout.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --output docs/dev_reports/t5201_t9000_research_quality_gate_closeout.md \
  --verdict PASS
```

## 25. Artifact Specification

Required quality gate artifacts:

- `quality_gate_summary.json`
- `robustness_scorecard.json`
- `data_quality_deep_audit.json`
- `split_leakage_report.json`
- `oos_validation_report.json`
- `parameter_stability.json`
- `parameter_fragility_report.json`
- `parameter_sensitivity_ranking.json`
- `strategy_robustness_report.json`
- `portfolio_robustness_report.json`
- `portfolio_overlap_risk.json`
- `correlation_proxy_report.json`
- `negative_control_report.json`
- `random_strategy_baseline.json`
- `shuffled_returns_baseline.json`
- `inverted_signal_baseline.json`
- `bootstrap_report.json`
- `bootstrap_confidence_intervals.json`
- `regime_breakdown.json`
- `regime_failure_report.json`
- `report_quality_check.json`
- `promotion_gate_v2.json`
- `reproducibility_manifest.json`
- `rerun_diff_report.json`
- `artifact_index.json`
- `report.md`
- `report.html`
- `manifest.json`

Manifest must contain:

- `release_hold=HOLD`
- `no_live=True`
- `no_submit=True`
- `no_exchange=True`
- `no_runtime_integration=True`
- `no_planner_integration=True`
- `no_network=True`
- `advisory_only=True`
- `human_review_required=True`
- `deterministic_seed`
- `input_artifact_hashes`
- `output_artifact_hashes`
- `generated_by`
- `quality_gate_version`
- `strict_mode=True`

Artifact shape rules:

- Every JSON artifact must include `schema_version`, `generated_by`, `deterministic_seed`, `release_hold`, `advisory_only`, `human_review_required`, `summary`, `warnings`, `hard_blocks`, and `verdict` where applicable.
- Every report artifact must include links or references to supporting artifacts.
- Every metric must define missing-data behavior.
- Every artifact must sort object keys and arrays deterministically where possible.

## 26. Architecture

Proposed layered architecture:

```text
scripts/
  run_multi_strategy_research_quality_gate.py
  run_strategy_robustness_lab.py
  run_parameter_robustness_lab.py
  run_portfolio_robustness_lab.py
  run_negative_control_lab.py
  run_bootstrap_research_lab.py
  run_regime_research_lab.py
  compare_research_quality_bundles.py
  build_research_quality_bundle.py
  generate_research_quality_closeout.py

core/
  research_quality_contract.py
  research_quality_gate_v2.py
  research_quality_score.py
  promotion_gate_v2.py
  data_quality_deep_audit*.py
  split_leakage_*.py
  oos_validation_*.py
  parameter_robustness_*.py
  strategy_robustness_*.py
  portfolio_robustness_*.py
  negative_control_*.py
  bootstrap_research_*.py
  regime_research_*.py
  report_quality_*.py
  research_artifact_hashing.py
  research_reproducibility_*.py
  research_quality_manifest.py
  research_quality_bundle.py
  research_quality_closeout.py
  research_safety_regression*.py

tests/
  unit/
  fixtures/research_quality/
    base/
    adversarial/
    negative_control/
    regime/
    bootstrap/
    expected/
```

Control flow:

1. Existing workbench creates `/tmp/multi_strategy_research_workbench`.
2. Quality gate reads only offline artifacts from that directory.
3. Data audit, split/OOS, parameter, strategy, portfolio, negative control, bootstrap, regime, report quality, promotion, reproducibility, and safety modules run.
4. Bundle writer writes all required artifacts.
5. Reproducibility manifest and hashes are generated.
6. Rerun writes second bundle.
7. Comparator validates deterministic equivalence.
8. Closeout generator writes final implementation evidence.
9. Final decision engine returns PASS/PARTIAL/FAIL.

## 27. Phase Plan T5201-T9000

### M1 — Baseline Guardrails / PRD-to-Implementation Contract (T5201-T5280)

Milestone commit rule: run targeted tests first, run `git status --short`, record frozen-file status, then use explicit `git add <listed files only>`. Never use `git add .`.

#### T5201-T5210

- Goal: Create implementation contract and safety constants for quality gate v2.
- Expected files: `core/research_quality_contract.py; tests/unit/test_research_quality_contract.py`.
- Tests: normal/edge/adversarial deterministic contract tests.
- Acceptance condition: contract exposes HOLD/advisory/human-review defaults and rejects non-HOLD.
- Safety checks: assert no network/exchange/runtime/planner imports; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5211-T5220

- Goal: Create artifact naming registry and required artifact inventory.
- Expected files: `core/research_quality_manifest.py; tests/unit/test_research_quality_manifest.py`.
- Tests: inventory shape, missing-artifact negative tests.
- Acceptance condition: all required artifacts are enumerated exactly once.
- Safety checks: registry contains no live/testnet artifact names; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5221-T5230

- Goal: Create fixture layout contract for base/adversarial/negative/regime/bootstrap/expected classes.
- Expected files: `tests/fixtures/research_quality/*/.gitkeep; core/research_fixture_contract.py; tests/unit/test_research_fixture_contract.py`.
- Tests: fixture existence and corruption negative tests.
- Acceptance condition: fixture classes are discoverable without loading full logs.
- Safety checks: chunked-only fixture scanner; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5231-T5240

- Goal: Create frozen-file and workspace guard specification helpers.
- Expected files: `core/research_safety_regression.py; tests/unit/test_research_safety_regression.py`.
- Tests: dirty workspace, frozen filename, git-add-dot evidence tests.
- Acceptance condition: guard reports PASS/PARTIAL/FAIL reasons.
- Safety checks: pre-existing untracked external state is ignored unless touched; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5241-T5250

- Goal: Create deterministic seed policy and stable JSON formatting helpers.
- Expected files: `core/research_reproducibility_seed.py; tests/unit/test_research_reproducibility_seed.py`.
- Tests: seed normal/invalid/repeatability tests.
- Acceptance condition: same input+seed produces byte-stable JSON.
- Safety checks: generated_at excluded only by comparator allowlist; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5251-T5260

- Goal: Create baseline quality bundle directory writer.
- Expected files: `core/research_quality_bundle.py; tests/unit/test_research_quality_bundle.py`.
- Tests: atomic write, overwrite, missing output-dir tests.
- Acceptance condition: bundle writes manifest + artifact_index skeleton deterministically.
- Safety checks: no network or exchange clients imported; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5261-T5270

- Goal: Create minimal acceptance harness shell with strict fail states.
- Expected files: `core/research_quality_acceptance.py; scripts/run_multi_strategy_research_quality_gate.py; tests/unit/test_research_quality_acceptance.py`.
- Tests: CLI args, strict mode, failure state tests.
- Acceptance condition: CLI exists but returns FAIL until required subsystems complete.
- Safety checks: no PASS possible with missing artifacts; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5271-T5280

- Goal: Milestone 1 closeout evidence.
- Expected files: `docs/dev_reports/t5201_t5280_research_quality_contract_evidence.md; tests/unit/test_research_quality_m1_evidence.py`.
- Tests: evidence artifact shape tests.
- Acceptance condition: targeted tests pass before explicit git add.
- Safety checks: frozen-file status and no-network assertion recorded; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

### M2 — Data Quality Deep Audit (T5281-T5600)

Milestone commit rule: run targeted tests first, run `git status --short`, record frozen-file status, then use explicit `git add <listed files only>`. Never use `git add .`.

#### T5281-T5310

- Goal: Implement OHLCV row validator with impossible OHLC, zero volume, NaN detection.
- Expected files: `core/data_quality_deep_audit.py; tests/unit/test_data_quality_deep_audit_rows.py`.
- Tests: valid, edge, corrupted, deterministic tests.
- Acceptance condition: invalid rows produce reason-coded findings.
- Safety checks: offline fixture-only parsing; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5311-T5340

- Goal: Implement timestamp monotonicity, duplicate bar, missing bar audit.
- Expected files: `core/data_quality_deep_audit_timestamps.py; tests/unit/test_data_quality_deep_audit_timestamps.py`.
- Tests: gap/duplicate/non-monotonic fixtures.
- Acceptance condition: bar audit summarizes counts and severity.
- Safety checks: does not load full CSV into context; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5341-T5370

- Goal: Implement stale coverage and symbol/timeframe coverage audit.
- Expected files: `core/data_quality_coverage_audit.py; tests/unit/test_data_quality_coverage_audit.py`.
- Tests: fresh/stale/partial/insufficient coverage tests.
- Acceptance condition: coverage_status is deterministic per symbol/timeframe.
- Safety checks: no exchange lookup or network fallback; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5371-T5400

- Goal: Implement inconsistent split coverage detector.
- Expected files: `core/data_quality_split_coverage.py; tests/unit/test_data_quality_split_coverage.py`.
- Tests: aligned/misaligned split fixture tests.
- Acceptance condition: split coverage mismatch blocks promotion.
- Safety checks: split IDs hashed without leaking timestamps; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5401-T5430

- Goal: Implement fixture corruption detector.
- Expected files: `core/data_quality_fixture_corruption.py; tests/unit/test_data_quality_fixture_corruption.py`.
- Tests: truncated, wrong header, wrong type, poisoned file tests.
- Acceptance condition: corruption produces hard block with file fingerprint.
- Safety checks: reads samples/chunks only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5431-T5460

- Goal: Implement data audit report builder.
- Expected files: `core/data_quality_deep_audit_report.py; tests/unit/test_data_quality_deep_audit_report.py`.
- Tests: report shape, reason aggregation, stable order tests.
- Acceptance condition: data_quality_deep_audit.json matches required schema.
- Safety checks: advisory-only promotion status preserved; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5461-T5490

- Goal: Add adversarial data fixtures.
- Expected files: `tests/fixtures/research_quality/adversarial/data_quality/*; tests/unit/test_data_quality_adversarial_fixtures.py`.
- Tests: corrupt OHLC, duplicate, non-monotonic, sparse fixtures.
- Acceptance condition: all adversarial fixtures are detected.
- Safety checks: fixture loader rejects network paths; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5491-T5520

- Goal: Add expected data audit fixtures and golden outputs.
- Expected files: `tests/fixtures/research_quality/expected/data_quality/*; tests/unit/test_data_quality_expected_outputs.py`.
- Tests: golden stable JSON hash tests.
- Acceptance condition: expected output hashes are reproducible.
- Safety checks: timestamps excluded only through comparator rule; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5521-T5560

- Goal: Wire Data Quality audit into quality gate bundle.
- Expected files: `core/research_quality_gate_v2.py; tests/unit/test_research_quality_gate_data_quality_integration.py`.
- Tests: normal/edge/adversarial integration tests.
- Acceptance condition: missing/corrupt data creates hard block.
- Safety checks: release_hold remains HOLD; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5561-T5600

- Goal: Milestone 2 closeout evidence.
- Expected files: `docs/dev_reports/t5281_t5600_data_quality_deep_audit_evidence.md; tests/unit/test_research_quality_m2_evidence.py`.
- Tests: evidence completeness tests.
- Acceptance condition: targeted data quality tests pass before commit.
- Safety checks: explicit git add only; frozen status recorded; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

### M3 — Split / Leakage / OOS Validation (T5601-T5920)

Milestone commit rule: run targeted tests first, run `git status --short`, record frozen-file status, then use explicit `git add <listed files only>`. Never use `git add .`.

#### T5601-T5630

- Goal: Implement rolling split verifier.
- Expected files: `core/split_leakage_rolling.py; tests/unit/test_split_leakage_rolling.py`.
- Tests: valid/overlap/missing boundary tests.
- Acceptance condition: rolling splits enforce chronological no-overlap.
- Safety checks: no planner/runtime integration; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5631-T5660

- Goal: Implement anchored split verifier.
- Expected files: `core/split_leakage_anchored.py; tests/unit/test_split_leakage_anchored.py`.
- Tests: valid/short-span/overlap tests.
- Acceptance condition: anchored splits produce reason-coded rejections.
- Safety checks: offline only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5661-T5690

- Goal: Implement chronological ordering and boundary hash capture.
- Expected files: `core/split_boundary_hash.py; tests/unit/test_split_boundary_hash.py`.
- Tests: stable hash, order perturbation, collision-safety tests.
- Acceptance condition: split boundary hashes change when boundaries change.
- Safety checks: hashes exclude generated_at; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5691-T5720

- Goal: Implement leakage score model.
- Expected files: `core/split_leakage_score.py; tests/unit/test_split_leakage_score.py`.
- Tests: clean/leaky/ambiguous fixtures.
- Acceptance condition: leakage_score and block severity are deterministic.
- Safety checks: advisory-only status only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5721-T5750

- Goal: Implement OOS stability by split.
- Expected files: `core/oos_validation_report.py; tests/unit/test_oos_validation_report.py`.
- Tests: stable/unstable/sparse OOS tests.
- Acceptance condition: oos_validation_report.json produced with split-level metrics.
- Safety checks: no auto-promotion; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5751-T5780

- Goal: Implement rejected split reasons registry.
- Expected files: `core/split_rejection_reasons.py; tests/unit/test_split_rejection_reasons.py`.
- Tests: reason code coverage tests.
- Acceptance condition: all split blocks have human-readable reasons.
- Safety checks: report contains no secrets; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5781-T5810

- Goal: Add leakage adversarial fixtures.
- Expected files: `tests/fixtures/research_quality/adversarial/split_leakage/*; tests/unit/test_split_leakage_adversarial_fixtures.py`.
- Tests: train/test overlap, lookahead, shuffled boundary fixtures.
- Acceptance condition: all leakage fixtures fail strict gate.
- Safety checks: no external file reads; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5811-T5840

- Goal: Add expected split/OOS golden artifacts.
- Expected files: `tests/fixtures/research_quality/expected/split_oos/*; tests/unit/test_split_oos_expected_outputs.py`.
- Tests: hash-stable report tests.
- Acceptance condition: split_leakage_report.json and oos_validation_report.json stable.
- Safety checks: deterministic order; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5841-T5880

- Goal: Wire split/OOS into quality gate summary.
- Expected files: `core/research_quality_gate_v2.py; tests/unit/test_research_quality_gate_split_oos_integration.py`.
- Tests: required min split tests.
- Acceptance condition: min-oos-splits strict block works.
- Safety checks: release_hold remains HOLD; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5881-T5920

- Goal: Milestone 3 closeout evidence.
- Expected files: `docs/dev_reports/t5601_t5920_split_leakage_oos_evidence.md; tests/unit/test_research_quality_m3_evidence.py`.
- Tests: evidence report tests.
- Acceptance condition: targeted split/OOS tests pass before commit.
- Safety checks: explicit git add only; frozen status recorded; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

### M4 — Parameter Robustness Lab (T5921-T6320)

Milestone commit rule: run targeted tests first, run `git status --short`, record frozen-file status, then use explicit `git add <listed files only>`. Never use `git add .`.

#### T5921-T5960

- Goal: Implement parameter neighborhood perturbation grid.
- Expected files: `core/parameter_robustness_grid.py; tests/unit/test_parameter_robustness_grid.py`.
- Tests: normal, boundary, invalid budget tests.
- Acceptance condition: grid respects search budget and deterministic ordering.
- Safety checks: no runtime/planner import; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T5961-T6000

- Goal: Implement fragility score.
- Expected files: `core/parameter_fragility_report.py; tests/unit/test_parameter_fragility_report.py`.
- Tests: stable/fragile/sparse fixtures.
- Acceptance condition: parameter_fragility_report.json produced with reason codes.
- Safety checks: strict max fragility blocks promotion; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6001-T6040

- Goal: Implement overfit suspicion score.
- Expected files: `core/parameter_overfit_suspicion.py; tests/unit/test_parameter_overfit_suspicion.py`.
- Tests: smooth vs spike performance tests.
- Acceptance condition: overfit suspicion score increases on narrow peaks.
- Safety checks: advisory-only output; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6041-T6080

- Goal: Implement heatmap data generator.
- Expected files: `core/parameter_heatmap_data.py; tests/unit/test_parameter_heatmap_data.py`.
- Tests: shape, NaN, sparse grid tests.
- Acceptance condition: parameter_stability.json includes heatmap-ready data.
- Safety checks: stable JSON formatting; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6081-T6120

- Goal: Implement top-N stability and dominance stability.
- Expected files: `core/parameter_topn_stability.py; tests/unit/test_parameter_topn_stability.py`.
- Tests: rank swap, stable rank, dominance failure tests.
- Acceptance condition: top-N stability and dominance metrics are deterministic.
- Safety checks: no auto-promotion; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6121-T6160

- Goal: Implement sensitivity ranking.
- Expected files: `core/parameter_sensitivity_ranking.py; tests/unit/test_parameter_sensitivity_ranking.py`.
- Tests: single/multi-param perturbation tests.
- Acceptance condition: parameter_sensitivity_ranking.json produced.
- Safety checks: same seed same ranking; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6161-T6200

- Goal: Add adversarial parameter fixtures.
- Expected files: `tests/fixtures/research_quality/adversarial/parameter_robustness/*; tests/unit/test_parameter_robustness_adversarial_fixtures.py`.
- Tests: needle-in-haystack, budget abuse, NaN metric fixtures.
- Acceptance condition: fragile fixtures fail strict gate.
- Safety checks: offline only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6201-T6240

- Goal: Add expected parameter golden artifacts.
- Expected files: `tests/fixtures/research_quality/expected/parameter_robustness/*; tests/unit/test_parameter_robustness_expected_outputs.py`.
- Tests: hash-stable expected outputs.
- Acceptance condition: golden parameter artifacts match byte hashes.
- Safety checks: timestamp allowlist enforced; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6241-T6280

- Goal: Create parameter robustness CLI.
- Expected files: `scripts/run_parameter_robustness_lab.py; tests/unit/test_run_parameter_robustness_lab_cli.py`.
- Tests: CLI arg, missing input, strict failure tests.
- Acceptance condition: CLI writes all parameter artifacts or fails.
- Safety checks: no network/exchange imports; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6281-T6320

- Goal: Milestone 4 closeout evidence.
- Expected files: `docs/dev_reports/t5921_t6320_parameter_robustness_evidence.md; tests/unit/test_research_quality_m4_evidence.py`.
- Tests: evidence and artifact index tests.
- Acceptance condition: targeted parameter tests pass before commit.
- Safety checks: explicit git add only; frozen status recorded; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

### M5 — Strategy Robustness Lab (T6321-T6680)

Milestone commit rule: run targeted tests first, run `git status --short`, record frozen-file status, then use explicit `git add <listed files only>`. Never use `git add .`.

#### T6321-T6360

- Goal: Implement strategy-by-strategy stress test runner.
- Expected files: `core/strategy_robustness_lab.py; tests/unit/test_strategy_robustness_lab.py`.
- Tests: normal/sparse/adverse fixtures.
- Acceptance condition: strategy_robustness_report.json written.
- Safety checks: no exchange or live routing; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6361-T6400

- Goal: Implement regime sensitivity diagnostics per strategy.
- Expected files: `core/strategy_regime_sensitivity.py; tests/unit/test_strategy_regime_sensitivity.py`.
- Tests: trend/chop/volatility fixtures.
- Acceptance condition: strategy regime sensitivity captured per strategy.
- Safety checks: advisory-only blocks; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6401-T6440

- Goal: Implement symbol sensitivity diagnostics.
- Expected files: `core/strategy_symbol_sensitivity.py; tests/unit/test_strategy_symbol_sensitivity.py`.
- Tests: single-symbol, concentrated, broad symbol tests.
- Acceptance condition: symbol concentration warnings emitted.
- Safety checks: stable order; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6441-T6480

- Goal: Implement timeframe sensitivity diagnostics.
- Expected files: `core/strategy_timeframe_sensitivity.py; tests/unit/test_strategy_timeframe_sensitivity.py`.
- Tests: 5m/15m/missing timeframe tests.
- Acceptance condition: timeframe failure does not crash bundle.
- Safety checks: no network fallback; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6481-T6520

- Goal: Implement entry/exit behavior diagnostics.
- Expected files: `core/strategy_entry_exit_diagnostics.py; tests/unit/test_strategy_entry_exit_diagnostics.py`.
- Tests: normal, no-exit, adverse exit tests.
- Acceptance condition: entry/exit warnings are reason-coded.
- Safety checks: no order placement semantics; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6521-T6560

- Goal: Implement sparse/noisy/adverse fixture handling.
- Expected files: `core/strategy_sparse_noisy_handling.py; tests/unit/test_strategy_sparse_noisy_handling.py`.
- Tests: sparse/noisy/adverse fixtures.
- Acceptance condition: sparse signals produce uncertainty not false PASS.
- Safety checks: strict mode blocks insufficient evidence; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6561-T6600

- Goal: Add expected strategy robustness outputs.
- Expected files: `tests/fixtures/research_quality/expected/strategy_robustness/*; tests/unit/test_strategy_robustness_expected_outputs.py`.
- Tests: golden report hash tests.
- Acceptance condition: strategy report stable across reruns.
- Safety checks: deterministic seed used; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6601-T6640

- Goal: Create strategy robustness CLI.
- Expected files: `scripts/run_strategy_robustness_lab.py; tests/unit/test_run_strategy_robustness_lab_cli.py`.
- Tests: CLI normal/invalid/missing artifact tests.
- Acceptance condition: CLI writes report or fails nonzero.
- Safety checks: no network/exchange imports; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6641-T6680

- Goal: Milestone 5 closeout evidence.
- Expected files: `docs/dev_reports/t6321_t6680_strategy_robustness_evidence.md; tests/unit/test_research_quality_m5_evidence.py`.
- Tests: evidence tests.
- Acceptance condition: targeted strategy robustness tests pass before commit.
- Safety checks: explicit git add only; frozen status recorded; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

### M6 — Portfolio Robustness Lab (T6681-T7040)

Milestone commit rule: run targeted tests first, run `git status --short`, record frozen-file status, then use explicit `git add <listed files only>`. Never use `git add .`.

#### T6681-T6720

- Goal: Implement correlation proxy.
- Expected files: `core/portfolio_correlation_proxy.py; tests/unit/test_portfolio_correlation_proxy.py`.
- Tests: uncorrelated/correlated/sparse fixtures.
- Acceptance condition: correlation_proxy_report.json produced.
- Safety checks: advisory-only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6721-T6760

- Goal: Implement overlap score and same-bar collision analysis.
- Expected files: `core/portfolio_overlap_risk.py; tests/unit/test_portfolio_overlap_risk.py`.
- Tests: no-overlap/high-overlap/collision fixtures.
- Acceptance condition: portfolio_overlap_risk.json blocks high overlap in strict mode.
- Safety checks: no order submission; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6761-T6800

- Goal: Implement crowding score and exposure concentration.
- Expected files: `core/portfolio_crowding_concentration.py; tests/unit/test_portfolio_crowding_concentration.py`.
- Tests: balanced/concentrated/crowded tests.
- Acceptance condition: exposure warnings reason-coded.
- Safety checks: no live/testnet; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6801-T6840

- Goal: Implement strategy contribution stability.
- Expected files: `core/portfolio_contribution_stability.py; tests/unit/test_portfolio_contribution_stability.py`.
- Tests: stable vs one-strategy dominance tests.
- Acceptance condition: contribution instability blocks promotion.
- Safety checks: stable JSON order; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6841-T6880

- Goal: Implement portfolio degradation and drawdown proxy.
- Expected files: `core/portfolio_degradation_drawdown.py; tests/unit/test_portfolio_degradation_drawdown.py`.
- Tests: degradation, drawdown, missing data tests.
- Acceptance condition: portfolio_robustness_report.json produced.
- Safety checks: offline only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6881-T6920

- Goal: Add adversarial portfolio fixtures.
- Expected files: `tests/fixtures/research_quality/adversarial/portfolio_robustness/*; tests/unit/test_portfolio_robustness_adversarial_fixtures.py`.
- Tests: same-bar pileup, concentrated exposure, correlated loss fixtures.
- Acceptance condition: adversarial portfolio fixtures fail strict gate.
- Safety checks: no network; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6921-T6960

- Goal: Add expected portfolio golden artifacts.
- Expected files: `tests/fixtures/research_quality/expected/portfolio_robustness/*; tests/unit/test_portfolio_robustness_expected_outputs.py`.
- Tests: hash-stable reports.
- Acceptance condition: portfolio reports match expected artifacts.
- Safety checks: timestamp allowlist enforced; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T6961-T7000

- Goal: Create portfolio robustness CLI.
- Expected files: `scripts/run_portfolio_robustness_lab.py; tests/unit/test_run_portfolio_robustness_lab_cli.py`.
- Tests: CLI arg and strict failure tests.
- Acceptance condition: CLI writes portfolio artifacts or fails.
- Safety checks: no exchange import; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7001-T7040

- Goal: Milestone 6 closeout evidence.
- Expected files: `docs/dev_reports/t6681_t7040_portfolio_robustness_evidence.md; tests/unit/test_research_quality_m6_evidence.py`.
- Tests: evidence tests.
- Acceptance condition: targeted portfolio tests pass before commit.
- Safety checks: explicit git add only; frozen status recorded; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

### M7 — Negative Controls (T7041-T7360)

Milestone commit rule: run targeted tests first, run `git status --short`, record frozen-file status, then use explicit `git add <listed files only>`. Never use `git add .`.

#### T7041-T7080

- Goal: Implement random strategy baseline.
- Expected files: `core/negative_control_random_strategy.py; tests/unit/test_negative_control_random_strategy.py`.
- Tests: seeded random, unstable, deterministic tests.
- Acceptance condition: random_strategy_baseline.json reproducible.
- Safety checks: advisory only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7081-T7120

- Goal: Implement shuffled returns baseline.
- Expected files: `core/negative_control_shuffled_returns.py; tests/unit/test_negative_control_shuffled_returns.py`.
- Tests: shuffle seed, no-op, corrupted return tests.
- Acceptance condition: shuffled_returns_baseline.json reproducible.
- Safety checks: offline only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7121-T7160

- Goal: Implement permuted signal baseline.
- Expected files: `core/negative_control_permuted_signal.py; tests/unit/test_negative_control_permuted_signal.py`.
- Tests: permutation, missing signal, deterministic tests.
- Acceptance condition: permuted control underperforms expected real strategy.
- Safety checks: no planner import; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7161-T7200

- Goal: Implement inverted signal baseline.
- Expected files: `core/negative_control_inverted_signal.py; tests/unit/test_negative_control_inverted_signal.py`.
- Tests: inversion, flat, sparse signal tests.
- Acceptance condition: inverted_signal_baseline.json produced.
- Safety checks: no order semantics; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7201-T7240

- Goal: Implement random parameter baseline.
- Expected files: `core/negative_control_random_parameter.py; tests/unit/test_negative_control_random_parameter.py`.
- Tests: budget-limited random param tests.
- Acceptance condition: random parameter baseline is deterministic with seed.
- Safety checks: search budget enforced; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7241-T7280

- Goal: Implement negative control margin engine.
- Expected files: `core/negative_control_report.py; tests/unit/test_negative_control_report.py`.
- Tests: real-beats-control, real-fails-control, tie tests.
- Acceptance condition: negative_control_report.json blocks insufficient margin.
- Safety checks: min-negative-control-margin honored; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7281-T7320

- Goal: Add negative-control fixtures and expected outputs.
- Expected files: `tests/fixtures/research_quality/negative_control/*; tests/fixtures/research_quality/expected/negative_control/*; tests/unit/test_negative_control_expected_outputs.py`.
- Tests: control fixture and golden hash tests.
- Acceptance condition: controls fail when real strategy cannot beat baseline.
- Safety checks: release_hold HOLD; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7321-T7340

- Goal: Create negative control CLI.
- Expected files: `scripts/run_negative_control_lab.py; tests/unit/test_run_negative_control_lab_cli.py`.
- Tests: CLI strict/missing/seed tests.
- Acceptance condition: CLI writes all baseline artifacts or fails.
- Safety checks: no network/exchange imports; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7341-T7360

- Goal: Milestone 7 closeout evidence.
- Expected files: `docs/dev_reports/t7041_t7360_negative_controls_evidence.md; tests/unit/test_research_quality_m7_evidence.py`.
- Tests: evidence tests.
- Acceptance condition: targeted negative control tests pass before commit.
- Safety checks: explicit git add only; frozen status recorded; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

### M8 — Bootstrap / Monte Carlo / Regime Segmentation (T7361-T7800)

Milestone commit rule: run targeted tests first, run `git status --short`, record frozen-file status, then use explicit `git add <listed files only>`. Never use `git add .`.

#### T7361-T7400

- Goal: Implement deterministic bootstrap sampler.
- Expected files: `core/bootstrap_research_sampler.py; tests/unit/test_bootstrap_research_sampler.py`.
- Tests: seed/repeatability/small sample tests.
- Acceptance condition: same seed same samples and hashes.
- Safety checks: offline only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7401-T7440

- Goal: Implement confidence intervals for expectancy/win-rate/stability.
- Expected files: `core/bootstrap_confidence_intervals.py; tests/unit/test_bootstrap_confidence_intervals.py`.
- Tests: normal, skewed, sparse tests.
- Acceptance condition: bootstrap_confidence_intervals.json produced.
- Safety checks: NaN handled as warning/block; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7441-T7480

- Goal: Implement worst-case percentile and resampling stability.
- Expected files: `core/bootstrap_research_report.py; tests/unit/test_bootstrap_research_report.py`.
- Tests: worst percentile and instability tests.
- Acceptance condition: bootstrap_report.json produced.
- Safety checks: strict blocks weak lower bound; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7481-T7520

- Goal: Create bootstrap CLI.
- Expected files: `scripts/run_bootstrap_research_lab.py; tests/unit/test_run_bootstrap_research_lab_cli.py`.
- Tests: CLI iterations/seed/invalid tests.
- Acceptance condition: CLI enforces bootstrap-iterations and writes artifacts.
- Safety checks: no network; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7521-T7560

- Goal: Implement trend/chop/volatility buckets.
- Expected files: `core/regime_research_segmentation.py; tests/unit/test_regime_research_segmentation.py`.
- Tests: trend/chop/volatile/ambiguous tests.
- Acceptance condition: regime_breakdown.json segmentation deterministic.
- Safety checks: offline fixture-only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7561-T7600

- Goal: Implement BTC proxy regime compatibility.
- Expected files: `core/regime_btc_proxy_compatibility.py; tests/unit/test_regime_btc_proxy_compatibility.py`.
- Tests: compatible/incompatible/missing proxy tests.
- Acceptance condition: BTC proxy warnings do not fetch network data.
- Safety checks: no Binance; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7601-T7640

- Goal: Implement per-regime scorecard and failure detection.
- Expected files: `core/regime_failure_report.py; tests/unit/test_regime_failure_report.py`.
- Tests: single regime failure and concentration tests.
- Acceptance condition: regime_failure_report.json blocks dangerous concentration.
- Safety checks: advisory-only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7641-T7680

- Goal: Add bootstrap/regime fixtures and expected outputs.
- Expected files: `tests/fixtures/research_quality/bootstrap/*; tests/fixtures/research_quality/regime/*; tests/fixtures/research_quality/expected/bootstrap_regime/*; tests/unit/test_bootstrap_regime_expected_outputs.py`.
- Tests: fixture/golden/determinism tests.
- Acceptance condition: bootstrap and regime artifacts hash-stable.
- Safety checks: seed captured in manifest; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7681-T7740

- Goal: Create regime CLI.
- Expected files: `scripts/run_regime_research_lab.py; tests/unit/test_run_regime_research_lab_cli.py`.
- Tests: CLI required-regime-breakdown tests.
- Acceptance condition: CLI writes regime artifacts or fails.
- Safety checks: no network/exchange import; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7741-T7800

- Goal: Milestone 8 closeout evidence.
- Expected files: `docs/dev_reports/t7361_t7800_bootstrap_regime_evidence.md; tests/unit/test_research_quality_m8_evidence.py`.
- Tests: evidence tests.
- Acceptance condition: targeted bootstrap/regime tests pass before commit.
- Safety checks: explicit git add only; frozen status recorded; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

### M9 — Report Quality Gate / Promotion Gate v2 (T7801-T8280)

Milestone commit rule: run targeted tests first, run `git status --short`, record frozen-file status, then use explicit `git add <listed files only>`. Never use `git add .`.

#### T7801-T7840

- Goal: Implement report completeness checker.
- Expected files: `core/report_quality_check.py; tests/unit/test_report_quality_check.py`.
- Tests: complete/missing/empty sections tests.
- Acceptance condition: report_quality_check.json produced.
- Safety checks: human-readable warnings included; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7841-T7880

- Goal: Implement required sections and artifact cross-link validation.
- Expected files: `core/report_quality_crosslink.py; tests/unit/test_report_quality_crosslink.py`.
- Tests: missing link, broken artifact, duplicate link tests.
- Acceptance condition: all report links resolve inside bundle.
- Safety checks: no external URL dependency; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7881-T7920

- Goal: Implement metric consistency checker.
- Expected files: `core/report_quality_metric_consistency.py; tests/unit/test_report_quality_metric_consistency.py`.
- Tests: inconsistent summary/detail, NaN, empty metric tests.
- Acceptance condition: metric inconsistency blocks promotion.
- Safety checks: stable reason codes; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7921-T7960

- Goal: Implement markdown report generator.
- Expected files: `core/research_quality_markdown_report.py; tests/unit/test_research_quality_markdown_report.py`.
- Tests: required sections and warnings tests.
- Acceptance condition: report.md generated deterministically.
- Safety checks: advisory-only language present; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T7961-T8000

- Goal: Implement HTML report generator.
- Expected files: `core/research_quality_html_report.py; tests/unit/test_research_quality_html_report.py`.
- Tests: HTML structure, escaped content, no external asset tests.
- Acceptance condition: report.html generated with no remote resources.
- Safety checks: no network calls; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8001-T8040

- Goal: Implement composite quality score and evidence completeness scoring.
- Expected files: `core/research_quality_score.py; tests/unit/test_research_quality_score.py`.
- Tests: weighted score, missing evidence, hard block tests.
- Acceptance condition: quality_gate_summary.json includes score and confidence bands.
- Safety checks: release_hold remains HOLD; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8041-T8080

- Goal: Implement advisory-only promotion status and block reasons.
- Expected files: `core/promotion_gate_v2.py; tests/unit/test_promotion_gate_v2.py`.
- Tests: PASS/PARTIAL/FAIL, hard block, advisory status tests.
- Acceptance condition: promotion_gate_v2.json never promotes to runtime/testnet/live.
- Safety checks: human_review_required true; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8081-T8120

- Goal: Implement confidence band integration.
- Expected files: `core/research_quality_confidence_bands.py; tests/unit/test_research_quality_confidence_bands.py`.
- Tests: bootstrap/OOS/negative control integration tests.
- Acceptance condition: confidence bands appear in summary and promotion gate.
- Safety checks: strict mode blocks missing bands; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8121-T8160

- Goal: Add report quality expected artifacts.
- Expected files: `tests/fixtures/research_quality/expected/report_quality/*; tests/unit/test_report_quality_expected_outputs.py`.
- Tests: markdown/html/json golden tests.
- Acceptance condition: reports are deterministic except allowlisted timestamps.
- Safety checks: no external assets; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8161-T8220

- Goal: Wire promotion gate v2 into full quality gate CLI.
- Expected files: `core/research_quality_gate_v2.py; tests/unit/test_research_quality_gate_promotion_integration.py`.
- Tests: missing evidence, weak evidence, strong advisory tests.
- Acceptance condition: strict quality gate returns correct verdict.
- Safety checks: no live escalation; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8221-T8280

- Goal: Milestone 9 closeout evidence.
- Expected files: `docs/dev_reports/t7801_t8280_report_promotion_gate_evidence.md; tests/unit/test_research_quality_m9_evidence.py`.
- Tests: evidence tests.
- Acceptance condition: targeted report/promotion tests pass before commit.
- Safety checks: explicit git add only; frozen status recorded; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

### M10 — Reproducibility / Hashing / Bundle Comparison / Safety Regression (T8281-T8720)

Milestone commit rule: run targeted tests first, run `git status --short`, record frozen-file status, then use explicit `git add <listed files only>`. Never use `git add .`.

#### T8281-T8320

- Goal: Implement input and output artifact hashing.
- Expected files: `core/research_artifact_hashing.py; tests/unit/test_research_artifact_hashing.py`.
- Tests: hash stable, changed artifact, missing artifact tests.
- Acceptance condition: input_artifact_hashes and output_artifact_hashes captured.
- Safety checks: generated_at allowlist respected; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8321-T8360

- Goal: Implement reproducibility manifest.
- Expected files: `core/research_reproducibility_manifest.py; tests/unit/test_research_reproducibility_manifest.py`.
- Tests: manifest required fields tests.
- Acceptance condition: manifest contains all safety flags and deterministic seed.
- Safety checks: release_hold HOLD; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8361-T8400

- Goal: Implement rerun diff detector.
- Expected files: `core/research_rerun_diff.py; tests/unit/test_research_rerun_diff.py`.
- Tests: identical, allowed timestamp, real diff tests.
- Acceptance condition: rerun_diff_report.json captures differences.
- Safety checks: strict fails unexpected diff; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8401-T8440

- Goal: Implement bundle comparator CLI.
- Expected files: `scripts/compare_research_quality_bundles.py; tests/unit/test_compare_research_quality_bundles_cli.py`.
- Tests: identical hash, timestamp allowlist, mismatch tests.
- Acceptance condition: CLI supports require-identical-hashes.
- Safety checks: no external reads; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8441-T8480

- Goal: Implement artifact index builder.
- Expected files: `core/research_artifact_index.py; tests/unit/test_research_artifact_index.py`.
- Tests: complete/missing/duplicate index tests.
- Acceptance condition: artifact_index.json stable and complete.
- Safety checks: required artifacts all indexed; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8481-T8520

- Goal: Implement dirty workspace and frozen file guard evidence.
- Expected files: `core/research_workspace_guard.py; tests/unit/test_research_workspace_guard.py`.
- Tests: pre-existing untracked, touched frozen, clean workspace tests.
- Acceptance condition: pre-existing external state not modified; touched frozen fails.
- Safety checks: no git add dot evidence required; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8521-T8560

- Goal: Implement no-network/no-submit import scanner.
- Expected files: `core/research_no_network_import_guard.py; tests/unit/test_research_no_network_import_guard.py`.
- Tests: forbidden import fixtures, allowed import tests.
- Acceptance condition: network/exchange/runtime/planner imports fail safety regression.
- Safety checks: offline only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8561-T8600

- Goal: Implement safety regression report.
- Expected files: `core/research_safety_regression_report.py; tests/unit/test_research_safety_regression_report.py`.
- Tests: all flags, wrong flag, missing flag tests.
- Acceptance condition: safety regression artifacts prove no escalation.
- Safety checks: advisory_only true; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8601-T8660

- Goal: Implement build bundle CLI.
- Expected files: `scripts/build_research_quality_bundle.py; tests/unit/test_build_research_quality_bundle_cli.py`.
- Tests: bundle construction, missing artifact, strict tests.
- Acceptance condition: bundle build fails when required artifact missing.
- Safety checks: no external/network asset; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8661-T8720

- Goal: Milestone 10 closeout evidence.
- Expected files: `docs/dev_reports/t8281_t8720_repro_safety_evidence.md; tests/unit/test_research_quality_m10_evidence.py`.
- Tests: evidence tests.
- Acceptance condition: targeted reproducibility/safety tests pass before commit.
- Safety checks: explicit git add only; frozen status recorded; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

### M11 — Final Acceptance Harness / Closeout (T8721-T9000)

Milestone commit rule: run targeted tests first, run `git status --short`, record frozen-file status, then use explicit `git add <listed files only>`. Never use `git add .`.

#### T8721-T8760

- Goal: Implement one-shot full quality gate CLI orchestration.
- Expected files: `scripts/run_multi_strategy_research_quality_gate.py; core/research_quality_gate_v2.py; tests/unit/test_run_multi_strategy_research_quality_gate_full_cli.py`.
- Tests: full CLI arg matrix, fail-fast, strict tests.
- Acceptance condition: one-shot CLI writes all required artifacts or fails.
- Safety checks: no network/exchange/runtime/planner; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8761-T8800

- Goal: Implement rerun acceptance CLI behavior.
- Expected files: `core/research_quality_rerun_acceptance.py; tests/unit/test_research_quality_rerun_acceptance.py`.
- Tests: rerun output dir, seed, diff tests.
- Acceptance condition: rerun bundle comparable with identical hashes.
- Safety checks: generated_at allowlist only; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8801-T8840

- Goal: Implement final PASS/PARTIAL/FAIL decision engine.
- Expected files: `core/research_quality_final_decision.py; tests/unit/test_research_quality_final_decision.py`.
- Tests: full pass, targeted-only partial, missing CLI fail tests.
- Acceptance condition: PASS impossible unless all acceptance commands pass.
- Safety checks: release_hold HOLD required; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8841-T8880

- Goal: Implement closeout report generator.
- Expected files: `scripts/generate_research_quality_closeout.py; core/research_quality_closeout.py; tests/unit/test_generate_research_quality_closeout.py`.
- Tests: PASS/PARTIAL/FAIL closeout tests.
- Acceptance condition: docs/dev_reports/t5201_t9000_research_quality_gate_closeout.md generated.
- Safety checks: implementation evidence only; no promotion; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8881-T8920

- Goal: Add final acceptance fixture bundle and golden outputs.
- Expected files: `tests/fixtures/research_quality/base/final_acceptance/*; tests/fixtures/research_quality/expected/final_acceptance/*; tests/unit/test_research_quality_final_acceptance_expected.py`.
- Tests: end-to-end fixture hash tests.
- Acceptance condition: quality gate artifacts are complete and stable.
- Safety checks: no network; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8921-T8960

- Goal: Run targeted milestone test matrix and fix only authorized files.
- Expected files: `tests/unit/test_research_quality_acceptance_matrix.py; docs/dev_reports/t8921_t8960_targeted_test_matrix.md`.
- Tests: all milestone targeted suites aggregated.
- Acceptance condition: targeted matrix passes before full suite.
- Safety checks: explicit git add only; frozen status check; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8961-T8980

- Goal: Run mandatory acceptance commands and rerun comparison.
- Expected files: `docs/dev_reports/t8961_t8980_acceptance_command_evidence.md`.
- Tests: command-output evidence shape tests.
- Acceptance condition: pytest full suite, workbench, quality gate, comparator all pass.
- Safety checks: no submit/network/exchange observed; release_hold remains `HOLD`; advisory-only and human-review flags remain true.

#### T8981-T9000

- Goal: Generate final closeout and commit evidence.
- Expected files: `docs/dev_reports/t5201_t9000_research_quality_gate_closeout.md; manifest artifacts`.
- Tests: closeout evidence tests.
- Acceptance condition: final verdict PASS only if all artifacts and acceptance commands pass.
- Safety checks: explicit git add only; implementation complete; release_hold remains `HOLD`; advisory-only and human-review flags remain true.


## 28. Test Strategy

Every major feature must include:

- Normal test.
- Edge case test.
- Adversarial/negative test.
- Deterministic output test.
- Artifact shape test.
- Safety boundary test where applicable.

Test classes:

1. Contract tests.
2. Data quality tests.
3. Split leakage tests.
4. OOS validation tests.
5. Parameter robustness tests.
6. Strategy robustness tests.
7. Portfolio robustness tests.
8. Negative control tests.
9. Bootstrap/resampling tests.
10. Regime segmentation tests.
11. Report quality tests.
12. Promotion gate tests.
13. Reproducibility/hash tests.
14. Safety regression tests.
15. CLI tests.
16. Final acceptance tests.

Assertion target:

- 800-1500 unit/acceptance assertions across the wave.

Fixture requirements:

- Base fixtures.
- Edge fixtures.
- Corrupted fixtures.
- Adversarial fixtures.
- Negative control fixtures.
- Bootstrap fixtures.
- Regime fixtures.
- Expected golden artifacts.

No test may require network access, Binance, exchange credentials, testnet, runtime, or planner.

## 29. Acceptance Criteria

Final PASS requires all of the following:

1. Full unit suite passes.
2. Original workbench acceptance command passes.
3. Full quality gate CLI passes in strict mode.
4. Rerun quality gate produces comparable bundle.
5. Bundle comparator passes with identical hashes except allowlisted timestamp fields.
6. Closeout report is generated.
7. All required artifacts exist.
8. Manifest contains all required safety flags.
9. `release_hold=HOLD`.
10. `advisory_only=True`.
11. `human_review_required=True`.
12. No network/exchange/runtime/planner imports are introduced.
13. No frozen file is touched.
14. No `git add .` is used.
15. No live/testnet/submit/cancel/flatten/order placement path is added.
16. All milestone evidence reports exist.
17. Final closeout reports PASS.

PARTIAL conditions:

- Targeted tests pass but full suite not run.
- Full suite passes but acceptance CLIs not all run.
- Quality gate runs but rerun comparison missing.
- Closeout generated with incomplete evidence.
- Non-critical artifact warnings remain.

FAIL conditions:

- Quality gate CLI is missing.
- Required artifacts are missing.
- `release_hold != HOLD`.
- `advisory_only` is false.
- `human_review_required` is false.
- Any frozen file touched.
- Any network/exchange/runtime/planner import added.
- Any live/testnet/submit/cancel/flatten/order path introduced.
- Rerun comparison fails unexpectedly.
- Full suite fails.
- Executor claims PASS after schema-only scaffold.

## 30. Acceptance Commands

Mandatory acceptance commands:

```bash
PYTHONPATH=. .venv/bin/pytest -q
```

```bash
python3 scripts/run_multi_strategy_research_workbench.py \
  --fixture-dir tests/fixtures/historical_backtest_lab \
  --output-dir /tmp/multi_strategy_research_workbench \
  --strategies breakout,mean_reversion,momentum,volatility_compression \
  --symbols BTCUSDT,ETHUSDT \
  --timeframes 5m,15m \
  --split-mode rolling \
  --search-budget 120 \
  --chunk-size 25
```

```bash
python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --min-oos-splits 3 \
  --min-stability-score 0.60 \
  --max-parameter-fragility 0.40 \
  --max-overlap-risk 0.70 \
  --min-negative-control-margin 0.10 \
  --bootstrap-iterations 200 \
  --deterministic-seed 424242 \
  --require-negative-control \
  --require-regime-breakdown \
  --require-bootstrap \
  --require-reproducibility \
  --strict \
  --release-hold HOLD
```

Rerun quality gate with output dir:

```bash
python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate_rerun \
  --min-oos-splits 3 \
  --min-stability-score 0.60 \
  --max-parameter-fragility 0.40 \
  --max-overlap-risk 0.70 \
  --min-negative-control-margin 0.10 \
  --bootstrap-iterations 200 \
  --deterministic-seed 424242 \
  --require-negative-control \
  --require-regime-breakdown \
  --require-bootstrap \
  --require-reproducibility \
  --strict \
  --release-hold HOLD
```

```bash
python3 scripts/compare_research_quality_bundles.py \
  --left /tmp/multi_strategy_research_quality_gate \
  --right /tmp/multi_strategy_research_quality_gate_rerun \
  --require-identical-hashes \
  --allow-timestamp-fields generated_at
```

```bash
python3 scripts/generate_research_quality_closeout.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --output docs/dev_reports/t5201_t9000_research_quality_gate_closeout.md \
  --verdict PASS
```

Final git evidence commands:

```bash
git status --short
git diff --name-only
git diff --cached --name-only
```

Commit rule:

```bash
git add <explicit files only>
git commit -m "feat: add research quality gate hardening"
```

Never:

```bash
git add .
```

## 31. Performance Budget

The final quality gate should be suitable for offline CI-level execution.

Budgets:

- Full unit suite: repo-dependent, must not introduce pathological slowdown.
- Quality gate CLI on fixture workbench: target under 5 minutes.
- Bootstrap iterations default: 200 for acceptance fixtures.
- Parameter grid must enforce `--search-budget`.
- Fixture loaders must use chunked/sample-based reads for large CSV/JSONL/log artifacts.
- Reports must avoid embedding massive raw artifacts.
- HTML report must be local, small, and static.
- Hashing must stream file contents rather than loading huge files into memory where possible.

Performance failure conditions:

- Any module loads full large CSV/JSONL/log into agent context.
- Any CLI has unbounded grid expansion.
- Any bootstrap/resampling path ignores iteration limit.
- Any report embeds raw full fixture data.

## 32. Rollout Plan

Rollout is implementation-only after this PRD is approved.

Recommended rollout sequence:

1. M1 contract and safety baseline.
2. M2 data audit.
3. M3 split/OOS leakage.
4. M4 parameter robustness.
5. M5 strategy robustness.
6. M6 portfolio robustness.
7. M7 negative controls.
8. M8 bootstrap and regime.
9. M9 report quality and promotion gate.
10. M10 reproducibility and safety regression.
11. M11 final acceptance and closeout.

Each milestone must:

- Run targeted tests.
- Check `git status --short`.
- Check frozen file status.
- Check no-network/no-submit safety assertion where relevant.
- Use explicit git add only.
- Produce evidence before commit.

## 33. Risk Register

| Risk | Impact | Mitigation |
|---|---:|---|
| Executor creates schema-only scaffold | High | Anti-collapse rule; phase incomplete without tests, fixtures, artifacts |
| Hidden leakage in split logic | High | Rolling/anchored split verification, boundary hash, adversarial fixtures |
| Overfit parameters look strong | High | Perturbation grid, fragility score, top-N stability, negative controls |
| Random controls accidentally outperform | High | Strict negative control margin and fail condition |
| Non-deterministic artifacts | High | Seed control, stable JSON, artifact hashing, rerun comparator |
| Report claims confidence with missing evidence | High | Evidence completeness scoring and report quality gate |
| Safety regression accidentally imports exchange/runtime | Critical | Import scanner and safety regression report |
| Frozen files touched | Critical | Workspace/frozen guard every milestone |
| Full suite skipped | High | PASS impossible without full suite and acceptance commands |
| Workbench outputs too large | Medium | Chunked reads and no raw report embedding |
| HTML report external assets | Medium | Local static HTML only, no remote resources |
| Future executor claims PASS after targeted tests only | High | Targeted-only result must be PARTIAL |

## 34. Stop Conditions

Stop immediately and report FAIL if:

- Any frozen file is touched, staged, renamed, deleted, or formatted.
- Any code path imports Binance, exchange client, network, runtime, planner, secret, credential, live submit, cancel, flatten, or order placement.
- `release_hold` is not `HOLD`.
- `advisory_only` is false.
- `human_review_required` is false.
- Required quality gate CLI cannot be created.
- Required artifact inventory cannot be produced.
- Full suite fails and cannot be fixed within allowed files.
- Rerun reproducibility comparison fails with non-allowlisted diffs.
- Executor discovers current repo state differs materially from PRD assumptions and cannot isolate changes safely.
- Any required acceptance command cannot be run.

Stop and report PARTIAL if:

- Milestones are partially implemented with passing targeted tests but full acceptance remains incomplete.
- Full suite cannot be run due to environment limitation.
- Closeout evidence is incomplete.
- Bundle comparator has not been executed.

## 35. Closeout Evidence Requirements

Final closeout report:

- `docs/dev_reports/t5201_t9000_research_quality_gate_closeout.md`

Must include:

- Final verdict: PASS/PARTIAL/FAIL.
- Commit hash.
- Changed files list.
- Test summary.
- Full suite result.
- Workbench acceptance command result.
- Quality gate command result.
- Rerun command result.
- Bundle comparator result.
- Closeout generator result.
- Required artifact inventory.
- Manifest safety flags.
- Frozen-file status.
- Dirty workspace status.
- No-network/no-submit/no-exchange/runtime/planner assertion.
- Known warnings.
- Human review requirement.
- Reminder: research output is advisory only; no live/testnet/runtime promotion.

## 36. Future Work

Future waves may add:

- Larger offline historical fixture packs.
- More strategies.
- More portfolio risk metrics.
- More visualization formats.
- Stress tests with synthetic market regimes.
- Cost-aware parameter search.
- Research review UI.
- Human annotation workflow.
- Offline experiment registry.
- Cross-version benchmark comparison.

Future work must still preserve:

- Offline-only posture.
- No live/testnet submit.
- No exchange.
- No runtime/planner promotion.
- `release_hold=HOLD` unless a separate human-approved PRD changes it.

## 37. Future Claude Execution Prompt

Use this prompt in a fresh Claude / cc execution window after committing this PRD.

```text
Use Caveman / terse engineering mode. Output only FILES / TESTS / RESULT / NOTES. No greetings. No long explanations. No unrelated code.

Repo:
~/Documents/trae_projects/qq

Task:
Execute the full T5201-T9000 Multi-Strategy Research Workbench Deep Hardening Program from:

docs/dev_prd/multi_strategy_research_workbench_deep_hardening_10h_prd.md

Read first:
- docs/dev_prd/multi_strategy_research_workbench_deep_hardening_10h_prd.md
- docs/dev_prd/multi_strategy_research_workbench_prd.md
- docs/dev_reports/t4201_t5200_multi_strategy_research_workbench_closeout.md

Important:
This is implementation now, not PRD authoring.

Do not stop after writing schemas.
Do not stop after writing dataclasses.
Do not claim PASS unless full suite passes.
Do not claim PASS unless acceptance commands pass.
Do not claim PASS unless rerun reproducibility comparison passes.
Do not claim PASS unless closeout report is generated.
If only targeted tests pass, result must be PARTIAL.
If quality gate CLI is missing, result must be FAIL.
If artifacts are missing, result must be FAIL.
If release_hold != HOLD, result must be FAIL.
If any frozen file is touched, result must be FAIL.

Mandatory anti-shallow rule:
If a phase only creates a schema/dataclass without tests, negative cases, fixtures, and artifact output, it is incomplete.

Every major feature must have:
- normal test
- edge case test
- adversarial/negative test
- deterministic output test
- artifact shape test
- safety boundary test where applicable

Hard safety:
- Offline only.
- No network.
- No Binance.
- No exchange client.
- No testnet submit.
- No live trading.
- No order placement.
- No cancel.
- No flatten.
- No submit.
- No runtime integration.
- No planner integration.
- No secrets / credentials / API keys.
- release_hold must remain HOLD.
- T5201+ remains HUMAN_REVIEW_REQUIRED.
- Research output is advisory only.
- No auto-promotion to live/testnet/runtime.
- No modification of frozen backlog files.
- No git add .
- Explicit git add only.
- Do not load full CSV/JSONL/log files into context; use chunked/head/tail/rg summaries.

Important current repo condition:
There may be pre-existing untracked files in the working tree, including frozen filenames. Treat them as pre-existing external state. Do not stage, modify, delete, rename, format, import, or execute them.

Required final acceptance commands:

PYTHONPATH=. .venv/bin/pytest -q

python3 scripts/run_multi_strategy_research_workbench.py \
  --fixture-dir tests/fixtures/historical_backtest_lab \
  --output-dir /tmp/multi_strategy_research_workbench \
  --strategies breakout,mean_reversion,momentum,volatility_compression \
  --symbols BTCUSDT,ETHUSDT \
  --timeframes 5m,15m \
  --split-mode rolling \
  --search-budget 120 \
  --chunk-size 25

python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --min-oos-splits 3 \
  --min-stability-score 0.60 \
  --max-parameter-fragility 0.40 \
  --max-overlap-risk 0.70 \
  --min-negative-control-margin 0.10 \
  --bootstrap-iterations 200 \
  --deterministic-seed 424242 \
  --require-negative-control \
  --require-regime-breakdown \
  --require-bootstrap \
  --require-reproducibility \
  --strict \
  --release-hold HOLD

python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate_rerun \
  --min-oos-splits 3 \
  --min-stability-score 0.60 \
  --max-parameter-fragility 0.40 \
  --max-overlap-risk 0.70 \
  --min-negative-control-margin 0.10 \
  --bootstrap-iterations 200 \
  --deterministic-seed 424242 \
  --require-negative-control \
  --require-regime-breakdown \
  --require-bootstrap \
  --require-reproducibility \
  --strict \
  --release-hold HOLD

python3 scripts/compare_research_quality_bundles.py \
  --left /tmp/multi_strategy_research_quality_gate \
  --right /tmp/multi_strategy_research_quality_gate_rerun \
  --require-identical-hashes \
  --allow-timestamp-fields generated_at

python3 scripts/generate_research_quality_closeout.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --output docs/dev_reports/t5201_t9000_research_quality_gate_closeout.md \
  --verdict PASS

Final output only:
FILES
- ...

TESTS
- ...

RESULT
- PASS / PARTIAL / FAIL

NOTES
- include commit hash
- include whether full suite passed
- include whether acceptance commands passed
- include whether rerun reproducibility comparison passed
- include whether closeout report was generated
- include reminder that research output remains advisory only
```
