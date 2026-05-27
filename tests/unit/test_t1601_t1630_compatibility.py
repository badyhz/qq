"""T1605 - Compatibility tests for frozen backlog validation suite (T1601-T1605).

Verifies:
- Validator models are importable
- 22 frozen files still untracked
- release_hold is HOLD across the inventory
"""
from __future__ import annotations

import subprocess

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_validator import validate_report_data, validate_report_file
from core.frozen_backlog_validation_result import FrozenBacklogValidationResult, build_validation_result
from core.frozen_backlog_validation_check import FrozenBacklogValidationCheck


def test_validator_models_importable():
    """All validator models are importable and have expected types."""
    assert callable(validate_report_data)
    assert callable(validate_report_file)
    assert callable(build_validation_result)
    assert isinstance(FrozenBacklogValidationResult, type)
    assert isinstance(FrozenBacklogValidationCheck, type)


def test_frozen_files_still_untracked():
    """The 22 frozen backlog files remain untracked by git."""
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True, text=True, cwd="/Users/winnie/Documents/trae_projects/qq",
    )
    output = result.stdout
    frozen_paths = [
        "core/live_runner.py",
        "scripts/live_playbook.py",
        "scripts/submit_approved_candidates.py",
        "scripts/run_testnet_order_smoke.py",
        "scripts/run_signal_testnet_trial.py",
        "scripts/run_spot_testnet_acceptance.py",
        "scripts/safe_flatten_testnet_symbol.py",
        "scripts/replay_shadow_order_plans_as_testnet_dry.py",
        "scripts/submit_replayed_testnet_payload.py",
        "scripts/run_controlled_testnet_shift.py",
        "scripts/run_daily_shadow_scan_pipeline.py",
        "scripts/run_next_shadow_experiment_plan.py",
        "scripts/run_observation_shift_runtime.py",
        "scripts/run_remediation_shadow_only_loop.py",
        "scripts/run_replay_submit_batch.py",
        "scripts/run_right_breakout_param_observation.py",
        "scripts/run_right_breakout_scan_dry.py",
        "scripts/run_shadow_observation_experiments.py",
        "scripts/run_shadow_sample_collection_pipeline.py",
        "scripts/run_shadow_universe_collector.py",
        "scripts/verify_risk_release_flow.py",
        "scripts/verify_testnet_repair_scenarios.py",
    ]
    for fp in frozen_paths:
        assert fp in output or f"?? {fp}" in output, (
            f"{fp} appears tracked — frozen file contamination!"
        )


def test_inventory_release_hold_all_hold():
    """Every inventory record has release_hold='HOLD'."""
    for rec in FROZEN_BACKLOG_INVENTORY.records:
        assert rec.release_hold == "HOLD", (
            f"{rec.file_path} has release_hold={rec.release_hold!r}"
        )


def test_inventory_has_22_records():
    """Inventory contains exactly 22 records."""
    assert FROZEN_BACKLOG_INVENTORY.total_count == 22
    assert len(FROZEN_BACKLOG_INVENTORY.records) == 22


def test_validation_result_dataclass():
    """FrozenBacklogValidationResult is frozen and works correctly."""
    r = build_validation_result(
        is_valid=True,
        checks_passed=("a",),
        checks_failed=(),
        error_message="",
    )
    assert r.is_valid is True
    assert r.checks_passed == ("a",)
    assert r.checks_failed == ()
    assert r.error_message == ""
