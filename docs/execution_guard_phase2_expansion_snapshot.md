# Execution Guard Phase2 Expansion Snapshot

> Generated: 2026-05-27

## Current State

- HEAD: `71e34ca2797b283458c9ed9cd8ce395c1c0632eb`
- Tags: `execution-guard-phase1-frozen`, `execution-guard-phase2-safe-batch`
- Phase status: Phase0 COMPLETE, Phase1 COMPLETE, Phase2 EXPANDED (30 scripts guarded)

## 30 Guarded Scripts

Batch1 (5):
- validate_testnet_artifacts
- generate_runner_dry_run_report
- generate_gate_decision_dashboard
- generate_trading_system_health_dashboard
- generate_sample_collection_eod_report

Batch2 (5):
- audit_real_ohlcv_source_schema
- calculate_execution_quality_score
- generate_ohlcv_gap_validation_control_report_v1
- generate_real_ohlcv_source_mapping_v1
- validate_real_ohlcv_gap_candidates

Batch3 (5):
- analyze_post_entry_mfe_mae
- analyze_trade_lifecycle_performance
- evaluate_missing_klines_recovery
- evaluate_tp_sl_efficiency
- show_trade_stats

Batch4 (5):
- generate_daily_operator_checklist
- audit_price_field_source_trust
- generate_phase_control_report_v1
- generate_phase_control_report_v2
- generate_strategy_relaxation_suggestions

Batch5 (5):
- analyze_readiness_blocker_attribution
- diagnose_near_miss_strict_gap
- evaluate_strategy_promotion_rules
- generate_single_human_gated_execution_local_audit_manifest_v1
- map_readiness_blockers_to_actions

Batch6 (5):
- generate_human_confirmation_token_gate_v1
- generate_human_gated_execution_final_safety_gate_v1
- generate_human_gated_execution_wrapper_eligibility_report_v1
- generate_human_gated_execution_wrapper_phase_control_report_v1
- generate_single_human_gated_execution_command_preview_packet_v1

## Batch Status

| Batch | Scripts | Tests | Status |
|---|---|---|---|
| Batch1 | 5 | 30 | COMPLETE |
| Batch2 | 5 | 30 | COMPLETE |
| Batch3 | 5 | 24+6 skip | COMPLETE |
| Batch4 | 5 | 30 | COMPLETE |
| Batch5 | 5 | 30 | COMPLETE |
| Batch6 | 5 | 30 | COMPLETE |

## Coverage Metrics

- Guarded: 30
- Unguarded SAFE: 11
- KEEP_NEEDS_REVIEW: 1
- NOT_ELIGIBLE: 219
- Frozen: 22
- Coverage ratio: 30/41 = 73.2%

## Remaining Backlog

- Batch6: 5 (COMPLETE)
- Batch7-9: 11 remaining
- Estimated: 3 more batches to clear

## Frozen Boundary

- 22 frozen files: UNCHANGED
- core/live_runner.py: UNCHANGED
- NO UNFREEZE, NO runtime, NO planner

## Recommended Actions

A. Complete batch6, continue batch7
B. Hold at 30, validate completeness
C. Focus on docs/taxonomy refinement
