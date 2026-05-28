"""Tests for offline research runbooks.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

RUNBOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "runbooks"

REQUIRED_RUNBOOKS = [
    "run_full_offline_research_stack.md",
    "run_quality_gate_only.md",
    "run_artifact_browser_only.md",
    "run_comparison_analytics_only.md",
    "run_human_review_packet_only.md",
    "rerun_reproducibility_check.md",
    "validate_release_hold_boundary.md",
    "recover_from_failed_artifact_browser.md",
    "recover_from_failed_comparison.md",
    "recover_from_failed_human_review.md",
    "offline_stack_clean_tmp_outputs.md",
    "offline_stack_preflight_check.md",
    "offline_stack_postflight_check.md",
]

REQUIRED_SECTIONS = [
    "purpose",
    "prerequisites",
    "command",
    "expected output",
    "pass",
    "fail",
    "safety",
    "forbidden",
    "recovery",
]


class TestRunbooksExist:
    @pytest.mark.parametrize("runbook", REQUIRED_RUNBOOKS)
    def test_runbook_exists(self, runbook):
        fp = RUNBOOKS_DIR / runbook
        assert fp.is_file(), f"missing runbook: {runbook}"


class TestRunbookSections:
    @pytest.mark.parametrize("runbook", REQUIRED_RUNBOOKS)
    def test_runbook_has_required_sections(self, runbook):
        fp = RUNBOOKS_DIR / runbook
        if not fp.is_file():
            pytest.skip(f"runbook missing: {runbook}")
        text = fp.read_text().lower()
        for section in REQUIRED_SECTIONS:
            assert section in text, f"{runbook}: missing section '{section}'"


class TestRunbookSafety:
    @pytest.mark.parametrize("runbook", REQUIRED_RUNBOOKS)
    def test_runbook_mentions_safety(self, runbook):
        fp = RUNBOOKS_DIR / runbook
        if not fp.is_file():
            pytest.skip(f"runbook missing: {runbook}")
        text = fp.read_text().lower()
        assert "hold" in text, f"{runbook}: must mention HOLD"
