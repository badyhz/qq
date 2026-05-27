"""T1380 - Compatibility tests for frozen backlog decision models."""
from __future__ import annotations

import subprocess


EXISTING_FROZEN_FILE_COUNT = 11


class TestDecisionMatrixCompatibility:
    """Verify decision matrix models are importable and compatible."""

    def test_decision_matrix_importable(self):
        from core.frozen_backlog_decision_matrix import FrozenBacklogDecisionMatrix, build_decision_matrix
        from core.frozen_backlog_decision_item import FrozenBacklogDecisionItem, build_decision_item
        from core.frozen_backlog_action_policy import FrozenBacklogActionPolicy, build_action_policy
        from core.frozen_backlog_evidence_spec import FrozenBacklogEvidenceSpec, build_evidence_spec
        from core.frozen_backlog_risk_assessment import FrozenBacklogRiskAssessment, build_risk_assessment
        from core.frozen_backlog_promotion_gate import FrozenBacklogPromotionGate, build_promotion_gate
        from core.frozen_backlog_matrix_verdict import FrozenBacklogMatrixVerdict, build_verdict
        from core.frozen_backlog_decision_renderer import (
            render_decision_matrix_md,
            render_decision_item_md,
            render_action_policy_md,
            render_risk_assessment_md,
            render_matrix_verdict_md,
        )

        # Verify all are callable / usable
        assert FrozenBacklogDecisionMatrix is not None
        assert build_decision_matrix is not None
        assert render_decision_matrix_md is not None

    def test_renderer_produces_markdown(self):
        from core.frozen_backlog_decision_matrix import build_decision_matrix
        from core.frozen_backlog_matrix_verdict import build_verdict
        from core.frozen_backlog_decision_renderer import render_decision_matrix_md

        verdict = build_verdict(verdict="HOLD", notes="compat check")
        matrix = build_decision_matrix(matrix_id="COMPAT-1", verdict=verdict)
        md = render_decision_matrix_md(matrix)
        assert "Frozen Backlog Decision Matrix" in md
        assert "COMPAT-1" in md

    def test_release_hold_is_hold(self):
        from core.frozen_backlog_matrix_verdict import build_verdict

        v = build_verdict(verdict="HOLD")
        assert v.verdict == "HOLD"

    def test_existing_frozen_files_untouched(self):
        """Verify existing tracked frozen files are still present (not accidentally deleted)."""
        result = subprocess.run(
            ["git", "ls-files", "core/"],
            capture_output=True,
            text=True,
            cwd="/Users/winnie/Documents/trae_projects/qq",
        )
        tracked = [f for f in result.stdout.strip().split("\n") if f.startswith("core/frozen_")]
        assert len(tracked) >= EXISTING_FROZEN_FILE_COUNT, (
            f"Expected >= {EXISTING_FROZEN_FILE_COUNT} tracked frozen files, got {len(tracked)}: {tracked}"
        )
