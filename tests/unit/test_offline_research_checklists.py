"""Tests for offline research checklists.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

CHECKLISTS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "checklists"

REQUIRED_CHECKLISTS = [
    "offline_research_preflight_checklist.md",
    "offline_research_postflight_checklist.md",
    "quality_gate_review_checklist.md",
    "artifact_browser_review_checklist.md",
    "comparison_analytics_review_checklist.md",
    "human_review_signoff_checklist.md",
    "release_hold_safety_checklist.md",
    "agent_handoff_checklist.md",
    "new_experiment_intake_checklist.md",
    "final_closeout_checklist.md",
]

REQUIRED_ELEMENTS = [
    "id",
    "required",
    "evidence",
    "pass",
    "fail",
    "safety",
]


class TestChecklistsExist:
    @pytest.mark.parametrize("checklist", REQUIRED_CHECKLISTS)
    def test_checklist_exists(self, checklist):
        fp = CHECKLISTS_DIR / checklist
        assert fp.is_file(), f"missing checklist: {checklist}"


class TestChecklistSections:
    @pytest.mark.parametrize("checklist", REQUIRED_CHECKLISTS)
    def test_checklist_has_required_elements(self, checklist):
        fp = CHECKLISTS_DIR / checklist
        if not fp.is_file():
            pytest.skip(f"checklist missing: {checklist}")
        text = fp.read_text().lower()
        for elem in REQUIRED_ELEMENTS:
            assert elem in text, f"{checklist}: missing element '{elem}'"


class TestChecklistSafety:
    @pytest.mark.parametrize("checklist", REQUIRED_CHECKLISTS)
    def test_checklist_mentions_hold(self, checklist):
        fp = CHECKLISTS_DIR / checklist
        if not fp.is_file():
            pytest.skip(f"checklist missing: {checklist}")
        text = fp.read_text().lower()
        assert "hold" in text, f"{checklist}: must mention HOLD"
