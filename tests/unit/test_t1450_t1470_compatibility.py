"""T1458 - Compatibility tests for T1450-T1470 batch.

Verify models importable, 22 frozen files still untracked, release_hold = HOLD.
"""
from __future__ import annotations

import subprocess

# The 22 frozen untracked files (before T1450-T1458 batch was added)
_FROZEN_22 = {
    "core/live_runner.py",
    "scripts/live_playbook.py",
    "scripts/replay_shadow_order_plans_as_testnet_dry.py",
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
    "scripts/run_signal_testnet_trial.py",
    "scripts/run_spot_testnet_acceptance.py",
    "scripts/run_testnet_order_smoke.py",
    "scripts/safe_flatten_testnet_symbol.py",
    "scripts/submit_approved_candidates.py",
    "scripts/submit_replayed_testnet_payload.py",
    "scripts/verify_risk_release_flow.py",
    "scripts/verify_testnet_repair_scenarios.py",
}


def test_models_importable():
    """All T1450-T1455 models can be imported without error."""
    from core.human_approval_transcript import HumanApprovalTranscript
    from core.human_approval_transcript_renderer import (
        render_readiness_dimension_md,
        render_readiness_score_md,
        render_transcript_md,
        render_transcript_step_md,
    )
    from core.promotion_readiness_calculator import calculate_readiness
    from core.promotion_readiness_dimension import (
        PromotionReadinessDimension,
        ReadinessDimensionName,
    )
    from core.promotion_readiness_score import PromotionReadinessScore
    from core.transcript_step import StepType, TranscriptStep

    # Verify they are actual classes/functions
    assert PromotionReadinessScore is not None
    assert PromotionReadinessDimension is not None
    assert calculate_readiness is not None
    assert HumanApprovalTranscript is not None
    assert TranscriptStep is not None
    assert render_transcript_md is not None
    assert render_transcript_step_md is not None
    assert render_readiness_score_md is not None
    assert render_readiness_dimension_md is not None


def test_22_frozen_files_still_untracked():
    """The 22 frozen untracked files must still be untracked."""
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    )
    untracked = set(result.stdout.strip().splitlines()) - {""}
    # All 22 original frozen files must still be present in untracked
    missing = _FROZEN_22 - untracked
    assert not missing, f"frozen files no longer untracked: {missing}"


def test_release_hold_is_hold():
    """Runtime governance release hold verdict is HOLD."""
    from core.runtime_governance_readonly_release_hold_packet import (
        RuntimeGovernanceReadOnlyReleaseHoldPacket,
    )
    packet = RuntimeGovernanceReadOnlyReleaseHoldPacket()
    assert packet.final_verdict == "HOLD"
    assert packet.hold_active is True


def test_new_core_files_exist():
    """The 6 new core files exist on disk."""
    import os
    new_core = [
        "core/promotion_readiness_score.py",
        "core/promotion_readiness_dimension.py",
        "core/promotion_readiness_calculator.py",
        "core/human_approval_transcript.py",
        "core/transcript_step.py",
        "core/human_approval_transcript_renderer.py",
    ]
    for f in new_core:
        assert os.path.isfile(f), f"missing: {f}"
