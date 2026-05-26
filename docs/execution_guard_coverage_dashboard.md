# Execution Guard Coverage Dashboard

**Generated**: 2026-05-27
**Audit type**: Read-only (no code changes)
**Source**: T632 deep audit recalculation (T638 update, T648 batch4 recompute, T655 global docs sync)

---

## Inventory Summary

| Metric | Count |
|---|---|
| Total Python scripts in `scripts/` | 353 |
| Scripts with `def main()` | 185 |
| Scripts without `def main()` | 168 |
| Frozen scripts (21 scripts + `core/live_runner.py`) | 22 |
| Non-frozen scripts | 331 |
| Guarded scripts (`assert_dry_run_required`) | 41 |

## T632 Audit Breakdown

| Category | Count |
|---|---|
| Guarded (eligible, already protected) | 41 |
| SAFE remaining (eligible, unguarded) | 0 |
| KEEP_NEEDS_REVIEW | 1 |
| NOT_ELIGIBLE | 219 |
| **Total audited** | **266** |

## Coverage Ratios

| Ratio | Value | Formula |
|---|---|---|
| Guarded / (guarded + unguarded SAFE) | **100.0%** | 41 / 41 |
| Guarded / total `main()` scripts | **22.1%** | 41 / 185 |
| Guarded / non-frozen scripts | **12.3%** | 41 / 331 |
| SAFE backlog remaining | **0** | 41 eligible - 41 guarded |
| Batches to clear backlog (5/batch) | **0** | 0 remaining (all batches complete) |

## Phase Status

| Phase | Scope | Status | Batch detail |
|---|---|---|---|
| Phase0 | Core helpers + schema + contract tests | COMPLETE | 5 scripts guarded |
| Phase1 | Docs + CLI polish | COMPLETE | Documentation and CLI improvements |
| Phase2 | Guard injection batches | DONE | 41/41 eligible = 100.0% (batch1=5, batch2=5, batch3=5, batch4=5, batch5=5, batch6=5, batch7=5, batch8=5, batch9=1) |
| Phase3 | Remaining SAFE backlog | FROZEN | 0 scripts pending |
| Phase4 | Post-backlog | FROZEN | Blocked until Phase2 complete |

## Guarded Scripts (41)

| # | File | Phase |
|---|---|---|
| 1 | `scripts/audit_real_ohlcv_source_schema.py` | Phase0 |
| 2 | `scripts/calculate_execution_quality_score.py` | Phase0 |
| 3 | `scripts/generate_ohlcv_gap_validation_control_report_v1.py` | Phase0 |
| 4 | `scripts/generate_real_ohlcv_source_mapping_v1.py` | Phase0 |
| 5 | `scripts/validate_real_ohlcv_gap_candidates.py` | Phase0 |
| 6 | `scripts/validate_testnet_artifacts.py` | Phase2-batch1 |
| 7 | `scripts/generate_runner_dry_run_report.py` | Phase2-batch1 |
| 8 | `scripts/generate_gate_decision_dashboard.py` | Phase2-batch1 |
| 9 | `scripts/generate_trading_system_health_dashboard.py` | Phase2-batch1 |
| 10 | `scripts/generate_sample_collection_eod_report.py` | Phase2-batch1 |
| 11 | `scripts/analyze_post_entry_mfe_mae.py` | Phase2-batch3 |
| 12 | `scripts/analyze_trade_lifecycle_performance.py` | Phase2-batch3 |
| 13 | `scripts/evaluate_missing_klines_recovery.py` | Phase2-batch3 |
| 14 | `scripts/evaluate_tp_sl_efficiency.py` | Phase2-batch3 |
| 15 | `scripts/show_trade_stats.py` | Phase2-batch3 |
| 16 | `scripts/generate_daily_operator_checklist.py` | Phase2-batch4 |
| 17 | `scripts/audit_price_field_source_trust.py` | Phase2-batch4 |
| 18 | `scripts/generate_phase_control_report_v1.py` | Phase2-batch4 |
| 19 | `scripts/generate_phase_control_report_v2.py` | Phase2-batch4 |
| 20 | `scripts/generate_strategy_relaxation_suggestions.py` | Phase2-batch4 |
| 21 | `scripts/analyze_readiness_blocker_attribution.py` | Phase2-batch5 |
| 22 | `scripts/diagnose_near_miss_strict_gap.py` | Phase2-batch5 |
| 23 | `scripts/evaluate_strategy_promotion_rules.py` | Phase2-batch5 |
| 24 | `scripts/generate_single_human_gated_execution_local_audit_manifest_v1.py` | Phase2-batch5 |
| 25 | `scripts/map_readiness_blockers_to_actions.py` | Phase2-batch5 |
| 26 | `scripts/generate_human_confirmation_token_gate_v1.py` | Phase2-batch6 |
| 27 | `scripts/generate_human_gated_execution_final_safety_gate_v1.py` | Phase2-batch6 |
| 28 | `scripts/generate_human_gated_execution_wrapper_eligibility_report_v1.py` | Phase2-batch6 |
| 29 | `scripts/generate_human_gated_execution_wrapper_phase_control_report_v1.py` | Phase2-batch6 |
| 30 | `scripts/generate_single_human_gated_execution_command_preview_packet_v1.py` | Phase2-batch6 |
| 31 | `scripts/generate_single_human_gated_execution_wrapper_artifact_phase_control_report_v1.py` | Phase2-batch7 |
| 32 | `scripts/generate_single_human_gated_testnet_execution_wrapper_artifact_v1.py` | Phase2-batch7 |
| 33 | `scripts/generate_ohlcv_gap_manual_approval_artifact_v1.py` | Phase2-batch7 |
| 34 | `scripts/generate_ohlcv_gap_manual_approval_gate_report_v1.py` | Phase2-batch7 |
| 35 | `scripts/generate_ohlcv_gap_manual_review_packet_v1.py` | Phase2-batch7 |
| 36 | `scripts/generate_ohlcv_gap_manual_review_phase_control_report_v1.py` | Phase2-batch8 |
| 37 | `scripts/interpret_ohlcv_gap_manual_review_checklist_v1.py` | Phase2-batch8 |
| 38 | `scripts/generate_repeat_small_batch_candidate_refresh_packet_v1.py` | Phase2-batch8 |
| 39 | `scripts/generate_human_copy_paste_dry_run_readiness_packet_v1.py` | Phase2-batch8 |
| 40 | `scripts/verify_human_copy_paste_dry_run_command_v1.py` | Phase2-batch8 |
| 41 | `scripts/simulate_human_token_validation_v1.py` | Phase2-batch9 |

## KEEP_NEEDS_REVIEW (1)

| # | File | Reason |
|---|---|---|
| 1 | `scripts/review_trade_logic_evolution_with_klines.py` | HTTP capable (needs human review before guard) |

## Frozen Files (untouched)

- **22 files** (21 scripts + `core/live_runner.py`)
- All listed in `docs/remaining_high_risk_frozen_inventory.md`
- Policy: no commits, no modifications, no guard injection

## Key Observations

1. **Eligible guard coverage at 100.0%**: T684 batch8+batch9 added 6 more guarded scripts, bringing total guarded to 41/41 eligible. Phase2 DONE.
2. **Raw coverage at 22.1%**: 41 of 185 `main()` scripts guarded -- most are NOT_ELIGIBLE (219).
3. **0 batches remaining**: All SAFE backlog cleared. Phase2 complete.
4. **1 KEEP_NEEDS_REVIEW**: `review_trade_logic_evolution_with_klines.py` retains HTTP capability and needs human review before any guard work.
5. **Frozen block unchanged**: 22 frozen files remain untouched per policy.
