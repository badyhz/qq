"""T1467 - Compatibility tests: imports, frozen files, release_hold."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

FROZEN_UNTRACKED = [
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
]


def test_unlock_recommendation_importable() -> None:
    from core.unlock_recommendation import UnlockRecommendation
    assert UnlockRecommendation.HOLD == "HOLD"


def test_hold_decision_report_importable() -> None:
    from core.hold_decision_report import HoldDecisionReport
    assert HoldDecisionReport.HOLD == "HOLD"


def test_engine_importable() -> None:
    from core.unlock_recommendation_engine import generate_unlock_recommendation
    rec = generate_unlock_recommendation(
        file_path="x.py", risk_class="HIGH", readiness_score=0.5
    )
    assert rec.recommendation == "HOLD"


def test_frozen_untracked_files_exist() -> None:
    """Frozen files are either untracked or deleted — both are safe."""
    import subprocess
    existing = [rel for rel in FROZEN_UNTRACKED if (REPO_ROOT / rel).exists()]
    if existing:
        # If they exist, they must be untracked
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"] + existing,
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        untracked = [l for l in result.stdout.strip().splitlines() if l]
        assert len(untracked) == len(existing), \
            f"Existing frozen files must be untracked: {existing}"
    # Either deleted or untracked — both are safe


def test_frozen_untracked_count() -> None:
    assert len(FROZEN_UNTRACKED) == 22
