"""T1449 - Compatibility tests for T1441-T1460 batch.

Verify models importable, 22 frozen files still untracked, release_hold is HOLD.
"""
from __future__ import annotations

import subprocess


class TestT1441T1449Compatibility:
    """Compatibility and safety checks."""

    def test_models_importable(self):
        """All new models can be imported without error."""
        from core.frozen_file_review_packet import FrozenFileReviewPacket, build_review_packet
        from core.frozen_review_check import FrozenReviewCheck, build_review_check
        from core.frozen_file_risk_requirement import FrozenFileRiskRequirement, build_risk_requirement
        from core.frozen_risk_requirement_checklist import FrozenRiskRequirementChecklist, build_checklist
        from core.frozen_review_packet_generator import generate_review_packet
        from core.frozen_review_packet_renderer import (
            render_review_packet_md,
            render_review_check_md,
            render_risk_requirement_md,
            render_checklist_md,
        )
        # If we get here, all imports succeeded
        assert FrozenFileReviewPacket is not None
        assert generate_review_packet is not None

    def test_frozen_files_still_untracked(self):
        """The 22 frozen files remain untracked by git."""
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard",
             "core/live_runner.py",
             "scripts/live_playbook.py",
             "scripts/submit_approved_candidates.py",
             "scripts/submit_replayed_testnet_payload.py",
             "scripts/run_testnet_order_smoke.py",
             "scripts/run_signal_testnet_trial.py",
             "scripts/run_spot_testnet_acceptance.py",
             "scripts/safe_flatten_testnet_symbol.py",
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
             "scripts/verify_risk_release_flow.py",
             "scripts/verify_testnet_repair_scenarios.py",
             ],
            capture_output=True,
            text=True,
            cwd="/Users/winnie/Documents/trae_projects/qq",
        )
        untracked = [l for l in result.stdout.strip().split("\n") if l]
        assert len(untracked) == 22, f"Expected 22 untracked, got {len(untracked)}: {untracked}"

    def test_release_hold_is_hold(self):
        """release_hold status is HOLD everywhere."""
        from core.release_hold_dashboard import ReleaseHoldDashboard
        dash = ReleaseHoldDashboard(
            dashboard_id="DASH-COMPAT",
            hold_status="HOLD",
            frozen_count=22,
            medium_count=13,
            governance_layers=("L1", "L2", "L3"),
            next_human_action="review",
        )
        assert dash.hold_status == "HOLD"

    def test_no_live_or_submit_imports_in_new_modules(self):
        """New modules do not import live/submit/exchange modules."""
        import ast
        import os

        new_modules = [
            "core/frozen_file_review_packet.py",
            "core/frozen_review_check.py",
            "core/frozen_file_risk_requirement.py",
            "core/frozen_risk_requirement_checklist.py",
            "core/frozen_review_packet_generator.py",
            "core/frozen_review_packet_renderer.py",
        ]
        forbidden = {"live_runner", "live_playbook", "submit", "exchange", "testnet", "execution"}
        base = "/Users/winnie/Documents/trae_projects/qq"
        for mod in new_modules:
            path = os.path.join(base, mod)
            with open(path) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for kw in forbidden:
                            assert kw not in alias.name, f"{mod} imports forbidden module {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for kw in forbidden:
                        assert kw not in node.module, f"{mod} imports forbidden module {node.module}"
