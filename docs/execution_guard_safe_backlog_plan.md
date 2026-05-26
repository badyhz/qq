# Execution Guard SAFE Backlog Plan

**Generated**: 2026-05-27
**Audit type**: Read-only (no code changes)
**Source**: T632 deep audit — 26 remaining unguarded SAFE scripts
**Previous batches**: batch1=5, batch2=5, batch3=5, batch4=5, batch5=5, batch6=5 (30 guarded total)

---

## Current State

| Metric | Count |
|---|---|
| Already guarded (batch1-6) | 30 |
| SAFE backlog remaining | 11 |
| Target batches to clear backlog | 3 (batch7 through batch9, 5 per batch, final batch=1) |
| Remaining after batch6 (T666) | 11 (batch7 through batch9) |

---

## Batch4 — T636 Shortlist (DONE)

**Risk**: LOW
**Expected test count**: 30
**Dependency notes**: All 5 use `strategy_edge_common` or pure stdlib; no network, no order submission.

| # | Script | Group | Why batch4 |
|---|---|---|---|
| 1 | `generate_daily_operator_checklist.py` | Other | Pure stdlib; low coupling, safe to guard first |
| 2 | `audit_price_field_source_trust.py` | Shadow-pipeline | Pure stdlib audit; minimal side effects |
| 3 | `generate_phase_control_report_v1.py` | Shadow-pipeline | Pure stdlib; report-only output |
| 4 | `generate_phase_control_report_v2.py` | Shadow-pipeline | Pure stdlib; v2 of same report pipeline |
| 5 | `generate_strategy_relaxation_suggestions.py` | Other | Pure stdlib; score/suggestion only |

**Ordering rationale**: T636 already flagged these as ready. Mixing groups de-risks batch — one failure does not block the same pipeline.

---

## Batch5 — Shadow-pipeline group (DONE)

**Risk**: LOW
**Expected test count**: 30
**Dependency notes**: All 5 use `strategy_edge_common` or pure stdlib; no network, no order submission. Tightly coupled to same pipeline as batch4 items 3-4.

| # | Script | Group | Why batch5 |
|---|---|---|---|
| 1 | `analyze_readiness_blocker_attribution.py` | Shadow-pipeline | Pure stdlib; blocker analysis only |
| 2 | `diagnose_near_miss_strict_gap.py` | Shadow-pipeline | Pure stdlib; gap diagnostic only |
| 3 | `evaluate_strategy_promotion_rules.py` | Shadow-pipeline | Pure stdlib; rule evaluation only |
| 4 | `generate_phase_control_report_v2.py` | Shadow-pipeline | Already in batch4 — see note below |
| 5 | `map_readiness_blockers_to_actions.py` | Shadow-pipeline | Pure stdlib; blocker-to-action mapping only |

**NOTE**: `generate_phase_control_report_v2.py` appears in batch4 above. If batch4 guards it successfully, substitute batch5 item 4 with `generate_single_human_gated_execution_local_audit_manifest_v1.py` (execution-gate group, pure stdlib) to avoid double-counting.

**Ordering rationale**: Clear the shadow-pipeline cluster in one pass. All scripts share the same dependency surface; guarding them together lets integration tests validate the full pipeline in one run.

---

## Batch6 — Pure stdlib (simplest) — Execution-gate (5 of 7)

**Risk**: LOW
**Expected test count**: 30
**Dependency notes**: All 5 are pure stdlib (argparse, json, os, sys, typing). No strategy_edge_common, no pipeline coupling.

| # | Script | Group | Why batch6 |
|---|---|---|---|
| 1 | `generate_human_confirmation_token_gate_v1.py` | Execution-gate | Token gate; isolated entry point, fewest dependents |
| 2 | `generate_human_gated_execution_final_safety_gate_v1.py` | Execution-gate | Final safety gate; end of pipeline |
| 3 | `generate_human_gated_execution_wrapper_eligibility_report_v1.py` | Execution-gate | Eligibility report; no downstream consumer |
| 4 | `generate_human_gated_execution_wrapper_phase_control_report_v1.py` | Execution-gate | Phase control report; parallel to batch4-5 reports |
| 5 | `generate_single_human_gated_execution_command_preview_packet_v1.py` | Execution-gate | Preview packet; pure artifact generation |

**Ordering rationale**: Simplest scripts first — pure stdlib, no external deps. Start with the ones that have fewest downstream dependents.

---

## Batch7 — Pure stdlib — Execution-gate (2 of 7) + OHLCV-gap (3 of 5)

**Risk**: LOW
**Expected test count**: 30
**Dependency notes**: All 5 are pure stdlib. Execution-gate scripts generate tightly-coupled artifacts; OHLCV-gap scripts form a manual-review pipeline.

| # | Script | Group | Why batch7 |
|---|---|---|---|
| 1 | `generate_single_human_gated_execution_wrapper_artifact_phase_control_report_v1.py` | Execution-gate | Wrapper artifact report; end of sub-pipeline |
| 2 | `generate_single_human_gated_testnet_execution_wrapper_artifact_v1.py` | Execution-gate | Testnet wrapper artifact; testnet-only output |
| 3 | `generate_ohlcv_gap_manual_approval_artifact_v1.py` | OHLCV-gap | Manual approval artifact; upstream of review |
| 4 | `generate_ohlcv_gap_manual_approval_gate_report_v1.py` | OHLCV-gap | Gate report; approval-gate pair |
| 5 | `generate_ohlcv_gap_manual_review_packet_v1.py` | OHLCV-gap | Review packet; start of review sub-pipeline |

**Ordering rationale**: Finish remaining execution-gate scripts, then start the OHLCV-gap cluster. OHLCV-gap approval/gate pair sits upstream of review.

---

## Batch8 — Pure stdlib — OHLCV-gap (2 of 5) + Other (3 of 6)

**Risk**: LOW
**Expected test count**: 30
**Dependency notes**: All 5 are pure stdlib. OHLCV-gap scripts complete the manual-review pipeline. Other scripts are standalone utilities.

| # | Script | Group | Why batch8 |
|---|---|---|---|
| 1 | `generate_ohlcv_gap_manual_review_phase_control_report_v1.py` | OHLCV-gap | Phase control report; completes review sub-pipeline |
| 2 | `interpret_ohlcv_gap_manual_review_checklist_v1.py` | OHLCV-gap | Checklist interpreter; completes OHLCV-gap cluster |
| 3 | `generate_repeat_small_batch_candidate_refresh_packet_v1.py` | Other | Refresh packet; pure stdlib |
| 4 | `generate_human_copy_paste_dry_run_readiness_packet_v1.py` | Other | Readiness packet; pure stdlib |
| 5 | `verify_human_copy_paste_dry_run_command_v1.py` | Other | Command verifier; pure stdlib |

**Ordering rationale**: Finish OHLCV-gap cluster (manual-review pipeline fully guarded across batches 7-8). Then clear 3 easy Other-group scripts.

---

## Batch9 — strategy_edge_common (3) + pipeline-coupled (2)

**Risk**: MEDIUM
**Expected test count**: 30
**Dependency notes**: 3 scripts import `strategy_edge_common` (read_csv_rows, to_float_nan, etc.). 2 scripts are pipeline-coupled — they consume shared artifacts and depend on strategy_edge_common.

| # | Script | Group | Why batch9 |
|---|---|---|---|
| 1 | `evaluate_testnet_reset_readiness.py` | Other | strategy_edge_common; testnet evaluation only |
| 2 | `generate_strategy_candidate_score.py` | Other | strategy_edge_common; scoring only |
| 3 | `generate_symbol_side_recommendations.py` | Other | strategy_edge_common; recommendation only |
| 4 | `generate_one_shot_manual_submit_runbook_artifact_v1.py` | One-shot | Pipeline-coupled; runbook artifact |
| 5 | `generate_final_human_gated_one_shot_submit_phase_control_report_v1.py` | One-shot | Pipeline-coupled; phase control report |

**Ordering rationale**: strategy_edge_common scripts first (they import the shared module). Pipeline-coupled scripts last — they depend on strategy_edge_common and share artifact contracts. Higher risk due to coupling.

---

## Batch10 — Remaining (1)

**Risk**: LOW
**Expected test count**: 6 (1 script, minimal test vectors)
**Dependency notes**: Pure stdlib. Standalone script, no downstream consumers.

| # | Script | Group | Why batch10 |
|---|---|---|---|
| 1 | `simulate_human_token_validation_v1.py` | Execution-gate | Token validation simulation; pure stdlib |

**Ordering rationale**: Final script — pure stdlib, standalone. No pipeline coupling, no strategy_edge_common dependency.

---

## Batch Summary

| Batch | Scripts | Risk | Test Count | Primary Group | Status |
|---|---|---|---|---|---|
| batch4 | 5 | LOW | 30 | T636 shortlist | DONE |
| batch5 | 5 | LOW | 30 | Shadow-pipeline | DONE |
| batch6 | 5 | LOW | 30 | Execution-gate (pure stdlib) | DONE |
| batch7 | 5 | LOW | 30 | Execution-gate + OHLCV-gap (pure stdlib) | PENDING |
| batch8 | 5 | LOW | 30 | OHLCV-gap + Other (pure stdlib) | PENDING |
| batch9 | 5 | MEDIUM | 30 | Other (strategy_edge_common) + One-shot (pipeline-coupled) | PENDING |
| batch10 | 1 | LOW | 6 | Execution-gate (pure stdlib) | PENDING |
| **Total** | **26** | — | **186** | — | **batch6 DONE** |

---

## Dependency Complexity Order (batch7-9)

1. **Pure stdlib** (batch7-8, 10 scripts): No external deps. Simplest to guard. Includes all execution-gate and OHLCV-gap scripts.
2. **strategy_edge_common** (batch9 items 1-3): Import `strategy_edge_common` for CSV/JSON reading. Medium complexity.
3. **Pipeline-coupled** (batch9 items 4-5): Consume shared artifacts, depend on strategy_edge_common. Highest coupling risk.

## Risk Mitigation Notes

1. **Pure stdlib scripts (batch7-8)**: Lowest risk — no external deps, isolated entry points. Guard at CLI entry without breaking artifact contract.
2. **strategy_edge_common scripts (batch9 items 1-3)**: Medium risk — import shared module. Guard must not alter strategy_edge_common interface. Test read_csv_rows, to_float_nan calls.
3. **Pipeline-coupled scripts (batch9 items 4-5)**: Higher risk — consume shared artifacts from upstream scripts. Guard must preserve artifact output format and file paths.

## Completion Criteria

- All 26 scripts guarded across 10 batches (batch1-6 DONE + batch7-9 PENDING + batch10 PENDING)
- Coverage: 41/41 eligible scripts (100% of SAFE backlog)
- Guarded / non-frozen scripts: 30 / 331 = 9.1% (current) -> 41 / 331 = 12.4% (target)
- Frozen scripts (22): NEVER touched, per hard constraint
