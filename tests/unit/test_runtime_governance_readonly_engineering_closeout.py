"""Tests for runtime governance read-only engineering closeout -- T849."""

import pytest

from core.runtime_governance_readonly_engineering_closeout import (
    RuntimeGovernanceReadOnlyEngineeringCloseout,
    build_readonly_engineering_closeout,
    readonly_engineering_closeout_to_dict,
    readonly_engineering_closeout_to_markdown,
)


class TestBuildReadonlyEngineeringCloseout:
    """Test build_readonly_engineering_closeout defaults."""

    def test_completed_tasks_count(self):
        closeout = build_readonly_engineering_closeout()
        assert len(closeout.completed_tasks) == 23

    def test_final_status_pass(self):
        closeout = build_readonly_engineering_closeout()
        assert closeout.final_status == "PASS"

    def test_frozen_boundaries_present(self):
        closeout = build_readonly_engineering_closeout()
        assert len(closeout.frozen_boundaries) > 0
        assert "no live trading" in closeout.frozen_boundaries

    def test_no_live_auth_in_notes(self):
        closeout = build_readonly_engineering_closeout()
        combined = " ".join(closeout.notes)
        assert "No live authorization" in combined

    def test_deterministic(self):
        a = build_readonly_engineering_closeout()
        b = build_readonly_engineering_closeout()
        assert a == b
        assert readonly_engineering_closeout_to_dict(a) == readonly_engineering_closeout_to_dict(b)

    def test_frozen_dataclass(self):
        closeout = build_readonly_engineering_closeout()
        with pytest.raises(AttributeError):
            closeout.final_status = "FAIL"  # type: ignore[misc]


class TestReadonlyEngineeringCloseoutToDict:
    """Test readonly_engineering_closeout_to_dict."""

    def test_expected_keys(self):
        closeout = build_readonly_engineering_closeout()
        d = readonly_engineering_closeout_to_dict(closeout)
        expected_keys = {
            "completed_tasks",
            "regression_status",
            "evidence_status",
            "manual_review_status",
            "frozen_boundaries",
            "final_status",
            "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_regression_status(self):
        closeout = build_readonly_engineering_closeout()
        d = readonly_engineering_closeout_to_dict(closeout)
        assert d["regression_status"] == "PASS"

    def test_evidence_status(self):
        closeout = build_readonly_engineering_closeout()
        d = readonly_engineering_closeout_to_dict(closeout)
        assert d["evidence_status"] == "PASS"

    def test_manual_review_status(self):
        closeout = build_readonly_engineering_closeout()
        d = readonly_engineering_closeout_to_dict(closeout)
        assert d["manual_review_status"] == "PENDING"


class TestReadonlyEngineeringCloseoutToMarkdown:
    """Test readonly_engineering_closeout_to_markdown."""

    def test_contains_final_status(self):
        closeout = build_readonly_engineering_closeout()
        md = readonly_engineering_closeout_to_markdown(closeout)
        assert "PASS" in md

    def test_contains_frozen_boundaries(self):
        closeout = build_readonly_engineering_closeout()
        md = readonly_engineering_closeout_to_markdown(closeout)
        assert "no live trading" in md
        assert "no order placement" in md

    def test_contains_task_count(self):
        closeout = build_readonly_engineering_closeout()
        md = readonly_engineering_closeout_to_markdown(closeout)
        assert "23" in md

    def test_no_timestamps(self):
        closeout = build_readonly_engineering_closeout()
        md = readonly_engineering_closeout_to_markdown(closeout)
        # no ISO date patterns or "timestamp" mentions
        assert "timestamp" not in md.lower()
