"""T1617 - Tests for FrozenBacklogDiff and diff engine."""
from __future__ import annotations

import pytest

from core.frozen_backlog_diff import FrozenBacklogDiff
from core.frozen_backlog_diff_engine import diff_reports, has_changes
from core.frozen_diff_change import FrozenDiffChange


def _make_record(
    file_path: str,
    risk_class: str = "medium",
    category: str = "util",
    unlock_recommendation: str = "review",
    release_hold: str = "HOLD",
) -> dict:
    return {
        "record_id": f"rec-{file_path}",
        "file_path": file_path,
        "risk_class": risk_class,
        "category": category,
        "allowed_actions": (),
        "forbidden_actions": (),
        "required_evidence": (),
        "readiness_score": 0.5,
        "unlock_recommendation": unlock_recommendation,
        "release_hold": release_hold,
    }


def _make_report(records: list[dict]) -> dict:
    return {
        "summary": {
            "summary_id": "s1",
            "total_files": len(records),
            "high_risk_count": 0,
            "medium_risk_count": len(records),
            "release_hold": "HOLD",
            "no_live": True,
            "no_submit": True,
            "no_exchange": True,
            "no_runtime_integration": True,
            "no_planner_integration": True,
        },
        "records": records,
    }


class TestDiffIdenticalReports:
    def test_no_changes(self):
        r = [_make_record("a.py")]
        before = _make_report(r)
        after = _make_report(r)
        diff = diff_reports(before, after)
        assert not has_changes(diff)
        assert diff.added_files == ()
        assert diff.removed_files == ()
        assert diff.risk_class_changes == ()
        assert diff.recommendation_changes == ()
        assert diff.hold_changes == ()


class TestDiffAddedFile:
    def test_added_file_detected(self):
        before = _make_report([_make_record("a.py")])
        after = _make_report([_make_record("a.py"), _make_record("b.py")])
        diff = diff_reports(before, after)
        assert has_changes(diff)
        assert diff.added_files == ("b.py",)
        assert diff.removed_files == ()

    def test_multiple_added_files_sorted(self):
        before = _make_report([_make_record("a.py")])
        after = _make_report([
            _make_record("a.py"),
            _make_record("c.py"),
            _make_record("b.py"),
        ])
        diff = diff_reports(before, after)
        assert diff.added_files == ("b.py", "c.py")


class TestDiffRemovedFile:
    def test_removed_file_detected(self):
        before = _make_report([_make_record("a.py"), _make_record("b.py")])
        after = _make_report([_make_record("a.py")])
        diff = diff_reports(before, after)
        assert has_changes(diff)
        assert diff.removed_files == ("b.py",)
        assert diff.added_files == ()


class TestDiffRiskClassChange:
    def test_risk_class_change_detected(self):
        before = _make_report([_make_record("a.py", risk_class="medium")])
        after = _make_report([_make_record("a.py", risk_class="high")])
        diff = diff_reports(before, after)
        assert has_changes(diff)
        assert len(diff.risk_class_changes) == 1
        assert diff.risk_class_changes[0].file_path == "a.py"
        assert diff.risk_class_changes[0].old_value == "medium"
        assert diff.risk_class_changes[0].new_value == "high"


class TestDiffRecommendationChange:
    def test_recommendation_change_detected(self):
        before = _make_report([_make_record("a.py", unlock_recommendation="hold")])
        after = _make_report([_make_record("a.py", unlock_recommendation="review")])
        diff = diff_reports(before, after)
        assert has_changes(diff)
        assert len(diff.recommendation_changes) == 1
        assert diff.recommendation_changes[0].old_value == "hold"
        assert diff.recommendation_changes[0].new_value == "review"


class TestDiffSafetyFlagChange:
    def test_safety_flag_change_detected(self):
        before = _make_report([_make_record("a.py")])
        after = _make_report([_make_record("a.py")])
        # Safety flags are on summary level, not per-record.
        # Simulate via direct construction.
        change = FrozenDiffChange(
            file_path="a.py", field_name="no_live", old_value=True, new_value=False
        )
        diff = FrozenBacklogDiff(
            diff_id="d1",
            before_snapshot_id="b1",
            after_snapshot_id="a1",
            added_files=(),
            removed_files=(),
            risk_class_changes=(),
            category_changes=(),
            recommendation_changes=(),
            safety_flag_changes=(change,),
            hold_changes=(),
        )
        assert has_changes(diff)
        assert len(diff.safety_flag_changes) == 1


class TestDiffHoldChange:
    def test_hold_change_detected(self):
        before = _make_report([_make_record("a.py", release_hold="HOLD")])
        after = _make_report([_make_record("a.py", release_hold="RELEASED")])
        diff = diff_reports(before, after)
        assert has_changes(diff)
        assert len(diff.hold_changes) == 1
        assert diff.hold_changes[0].old_value == "HOLD"
        assert diff.hold_changes[0].new_value == "RELEASED"


class TestDiffCategoryChange:
    def test_category_change_detected(self):
        before = _make_report([_make_record("a.py", category="util")])
        after = _make_report([_make_record("a.py", category="core")])
        diff = diff_reports(before, after)
        assert has_changes(diff)
        assert len(diff.category_changes) == 1


class TestDiffDeterministic:
    def test_deterministic_output(self):
        r = [_make_record("a.py"), _make_record("b.py")]
        before = _make_report(r)
        after = _make_report(r)
        d1 = diff_reports(before, after, diff_id="x", before_snapshot_id="b", after_snapshot_id="a")
        d2 = diff_reports(before, after, diff_id="x", before_snapshot_id="b", after_snapshot_id="a")
        assert d1 == d2
        assert d1 is not d2


class TestDiffFrozenDataclass:
    def test_frozen_diff_immutable(self):
        r = [_make_record("a.py")]
        diff = diff_reports(_make_report(r), _make_report(r))
        with pytest.raises(AttributeError):
            diff.diff_id = "changed"  # type: ignore[misc]

    def test_frozen_change_immutable(self):
        c = FrozenDiffChange(file_path="a.py", field_name="x", old_value=1, new_value=2)
        with pytest.raises(AttributeError):
            c.old_value = 99  # type: ignore[misc]


class TestDiffIdFields:
    def test_snapshot_ids_preserved(self):
        r = [_make_record("a.py")]
        diff = diff_reports(
            _make_report(r), _make_report(r),
            diff_id="d42", before_snapshot_id="snap1", after_snapshot_id="snap2",
        )
        assert diff.diff_id == "d42"
        assert diff.before_snapshot_id == "snap1"
        assert diff.after_snapshot_id == "snap2"
