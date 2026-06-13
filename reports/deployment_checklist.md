# Deployment Dry-run Checklist

**Total steps:** 7

## Checklist

- [ ] **verify_core_modules**: Verify all required core modules are present
  - Simulation only: True
  - Human approval required: True
- [ ] **verify_runner_scripts**: Verify all runner scripts are present
  - Simulation only: True
  - Human approval required: True
- [ ] **verify_test_suite**: Verify test suite passes (dry-run: check only)
  - Simulation only: True
  - Human approval required: True
- [ ] **verify_no_real_submit**: Verify no real submit permissions are enabled
  - Simulation only: True
  - Human approval required: True
- [ ] **verify_dry_run_mode**: Verify system is in dry-run mode
  - Simulation only: True
  - Human approval required: True
- [ ] **generate_deployment_manifest**: Generate deployment manifest with hashes
  - Simulation only: True
  - Human approval required: True
- [ ] **generate_deployment_checklist**: Generate human-readable deployment checklist
  - Simulation only: True
  - Human approval required: True

## Required Core Modules

- `core/alert_center.py`
- `core/alert_source_adapter_registry.py`
- `core/dangerous_runtime_isolator.py`
- `core/deployment_dry_run_pack.py`
- `core/final_handoff_pack.py`
- `core/frozen_cleanup_decision_matrix.py`
- `core/frozen_cleanup_dry_run_executor.py`
- `core/frozen_cleanup_evidence_recorder.py`
- `core/frozen_cleanup_final_inventory.py`
- `core/frozen_cleanup_handoff_pack.py`
- `core/frozen_cleanup_report.py`
- `core/operator_console.py`
- `core/operator_dashboard_renderer.py`
- `core/promotion_approval_packet.py`
- `core/promotion_decision_engine.py`
- `core/promotion_evidence_loader.py`
- `core/promotion_rollback_plan.py`
- `core/research_artifact_registry.py`
- `core/safe_archive_planner.py`
- `core/shadow_pipeline_registry.py`
- `core/strategy_promotion_board.py`
- `core/strategy_registry.py`
- `core/testnet_dry_run_adapter_registry.py`
- `core/testnet_dry_run_orchestrator.py`
- `core/untracked_runtime_inventory.py`

## Required Runner Scripts

- `scripts/run_alert_center_dry_run.py`
- `scripts/run_alert_source_adapter_registry.py`
- `scripts/run_dangerous_runtime_isolation.py`
- `scripts/run_frozen_cleanup_governance.py`
- `scripts/run_operator_dashboard.py`
- `scripts/run_phase5_final.py`
- `scripts/run_promotion_gate.py`
- `scripts/run_research_artifact_registry.py`
- `scripts/run_shadow_pipeline_registry.py`
- `scripts/run_strategy_registry.py`
- `scripts/run_testnet_dry_run_adapter_registry.py`
- `scripts/run_untracked_runtime_inventory.py`
