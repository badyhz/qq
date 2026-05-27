"""T1618 - Tests for FrozenBacklogVerdictEngine."""
from __future__ import annotations

import pytest

from core.frozen_backlog_diff import FrozenBacklogDiff
from core.frozen_backlog_diff_engine import diff_reports
from core.frozen_backlog_validation_result import build_validation_result
from core.frozen_backlog_verdict import FrozenBacklogVerdict, build_verdict
from core.frozen_backlog_verdict_engine import compute_verdict
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


def _valid_result():
    return build_validation_result(True, ("all",), ())


def _invalid_result(msg="bad"):
    return build_validation_result(False, (), ("fail",), msg)


class TestPassVerdict:
    def test_no_changes_valid(self):
        r = [_make_record("a.py")]
        diff = diff_reports(_make_report(r), _make_report(r))
        v = compute_verdict(diff, _valid_result())
        assert v.verdict == "PASS"
        assert v.risk_level == "SAFE"
        assert v.changed_fields == ()

    def test_empty_diff_passes(self):
        diff = FrozenBacklogDiff(
            diff_id="d1", before_snapshot_id="b", after_snapshot_id="a",
            added_files=(), removed_files=(),
            risk_class_changes=(), category_changes=(),
            recommendation_changes=(), safety_flag_changes=(), hold_changes=(),
        )
        v = compute_verdict(diff, _valid_result())
        assert v.verdict == "PASS"


class TestPartialVerdict:
    def test_recommendation_change_partial(self):
        before = _make_report([_make_record("a.py", unlock_recommendation="hold")])
        after = _make_report([_make_record("a.py", unlock_recommendation="review")])
        diff = diff_reports(before, after)
        v = compute_verdict(diff, _valid_result())
        assert v.verdict == "PARTIAL"
        assert v.risk_level == "CAUTION"
        assert len(v.changed_fields) > 0

    def test_category_change_partial(self):
        before = _make_report([_make_record("a.py", category="util")])
        after = _make_report([_make_record("a.py", category="core")])
        diff = diff_reports(before, after)
        v = compute_verdict(diff, _valid_result())
        assert v.verdict == "PARTIAL"


class TestFailVerdict:
    def test_safety_flag_change_fail(self):
        change = FrozenDiffChange(
            file_path="a.py", field_name="no_live", old_value=True, new_value=False
        )
        diff = FrozenBacklogDiff(
            diff_id="d1", before_snapshot_id="b", after_snapshot_id="a",
            added_files=(), removed_files=(),
            risk_class_changes=(), category_changes=(),
            recommendation_changes=(),
            safety_flag_changes=(change,),
            hold_changes=(),
        )
        v = compute_verdict(diff, _valid_result())
        assert v.verdict == "FAIL"
        assert v.risk_level == "CRITICAL"

    def test_hold_change_fail(self):
        before = _make_report([_make_record("a.py", release_hold="HOLD")])
        after = _make_report([_make_record("a.py", release_hold="RELEASED")])
        diff = diff_reports(before, after)
        v = compute_verdict(diff, _valid_result())
        assert v.verdict == "FAIL"
        assert v.risk_level == "CRITICAL"

    def test_risk_class_change_fail(self):
        before = _make_report([_make_record("a.py", risk_class="medium")])
        after = _make_report([_make_record("a.py", risk_class="high")])
        diff = diff_reports(before, after)
        v = compute_verdict(diff, _valid_result())
        assert v.verdict == "FAIL"
        assert v.risk_level == "CRITICAL"

    def test_added_file_fail(self):
        before = _make_report([_make_record("a.py")])
        after = _make_report([_make_record("a.py"), _make_record("b.py")])
        diff = diff_reports(before, after)
        v = compute_verdict(diff, _valid_result())
        assert v.verdict == "FAIL"

    def test_removed_file_fail(self):
        before = _make_report([_make_record("a.py"), _make_record("b.py")])
        after = _make_report([_make_record("a.py")])
        diff = diff_reports(before, after)
        v = compute_verdict(diff, _valid_result())
        assert v.verdict == "FAIL"


class TestFailOnInvalidValidation:
    def test_validation_fail(self):
        r = [_make_record("a.py")]
        diff = diff_reports(_make_report(r), _make_report(r))
        v = compute_verdict(diff, _invalid_result())
        assert v.verdict == "FAIL"
        assert v.risk_level == "CRITICAL"
        assert "Validation failed" in v.notes


class TestVerdictFrozen:
    def test_verdict_immutable(self):
        v = build_verdict("PASS", "ok", (), "SAFE")
        with pytest.raises(AttributeError):
            v.verdict = "FAIL"  # type: ignore[misc]


class TestCountChangeFail:
    def test_total_files_change_fail(self):
        """Simulate count change via direct diff construction with added files."""
        before = _make_report([_make_record("a.py"), _make_record("b.py")])
        after = _make_report([_make_record("a.py")])
        diff = diff_reports(before, after)
        v = compute_verdict(diff, _valid_result())
        assert v.verdict == "FAIL"
        assert "removed_files" in v.changed_fields or "removed_files" in str(v.changed_fields)
