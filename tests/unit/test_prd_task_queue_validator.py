"""Tests for PRD task queue validator — T867.

Pure, deterministic, no I/O, no timestamps, no random.
"""

import pytest

from core.prd_task_model import PrdTask
from core.prd_task_queue_validator import (
    PrdTaskQueueValidationReport,
    PrdTaskValidationIssue,
    validate_prd_task_queue,
    validate_task_range_contiguous,
    validation_report_to_dict,
    validation_report_to_markdown,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(
    task_id: str,
    status: str = "NOT_STARTED",
    risk_level: str = "LOW",
    title: str = "",
) -> PrdTask:
    return PrdTask(
        task_id=task_id,
        title=title or f"Task {task_id}",
        status=status,
        allowed_files=[],
        dependencies=[],
        acceptance_commands=[],
        risk_level=risk_level,
        notes=[],
    )


def _make_range(start: str, end: str, statuses=None, risks=None) -> list[PrdTask]:
    """Create tasks T<start_num>..T<end_num>."""
    s = int(start[1:])
    e = int(end[1:])
    tasks = []
    for i in range(s, e + 1):
        tid = f"T{i}"
        st = statuses[i - s] if statuses and (i - s) < len(statuses) else "NOT_STARTED"
        rk = risks[i - s] if risks and (i - s) < len(risks) else "LOW"
        tasks.append(_make_task(tid, status=st, risk_level=rk))
    return tasks


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestValidRange:
    """T865-T872 contiguous, valid → PASS."""

    def test_valid_range_passes(self):
        tasks = _make_range("T865", "T872")
        report = validate_prd_task_queue(tasks, "T865", "T872")
        assert report.final_verdict == "PASS"
        assert report.total_tasks == 8
        assert report.issue_count == 0
        assert report.blocker_count == 0
        assert report.warning_count == 0

    def test_empty_task_list(self):
        report = validate_prd_task_queue([], "T865", "T872")
        assert report.final_verdict == "BLOCKED"
        assert report.total_tasks == 0
        # Missing start + missing end
        assert report.blocker_count == 2


class TestDuplicate:
    """Duplicate task IDs → BLOCKED."""

    def test_duplicate_task_blocked(self):
        tasks = [_make_task("T865"), _make_task("T865")]
        report = validate_prd_task_queue(tasks, "T865", "T865")
        assert report.final_verdict == "BLOCKED"
        dup_issues = [i for i in report.issues if i.category == "duplicate"]
        assert len(dup_issues) == 1


class TestMissingTask:
    """Missing start/end task → BLOCKED."""

    def test_missing_start_blocked(self):
        tasks = [_make_task("T870")]
        report = validate_prd_task_queue(tasks, "T865", "T870")
        assert report.final_verdict == "BLOCKED"
        missing = [i for i in report.issues if i.category == "missing_range"]
        assert len(missing) == 1
        assert "T865" in missing[0].message

    def test_missing_end_blocked(self):
        tasks = [_make_task("T865")]
        report = validate_prd_task_queue(tasks, "T865", "T870")
        assert report.final_verdict == "BLOCKED"
        missing = [i for i in report.issues if i.category == "missing_range"]
        assert len(missing) == 1
        assert "T870" in missing[0].message

    def test_both_missing_blocked(self):
        tasks = [_make_task("T868")]
        report = validate_prd_task_queue(tasks, "T865", "T870")
        assert report.final_verdict == "BLOCKED"
        missing = [i for i in report.issues if i.category == "missing_range"]
        assert len(missing) == 2


class TestInvalidID:
    """Invalid task ID format → FAIL (structural invalidity)."""

    def test_invalid_id_fails(self):
        tasks = [_make_task("BAD"), _make_task("T865")]
        report = validate_prd_task_queue(tasks, "T865", "T865")
        assert report.final_verdict == "FAIL"
        inv = [i for i in report.issues if i.category == "invalid_id"]
        assert len(inv) == 1
        assert inv[0].task_id == "BAD"

    def test_only_invalid_ids_fails(self):
        tasks = [_make_task("X1"), _make_task("Y2")]
        report = validate_prd_task_queue(tasks, "T865", "T866")
        assert report.final_verdict == "FAIL"
        inv = [i for i in report.issues if i.category == "invalid_id"]
        assert len(inv) == 2


class TestForbiddenStatuses:
    """HUMAN_REVIEW_REQUIRED / FROZEN → warning, must not auto-execute."""

    def test_human_review_required_warning(self):
        tasks = [
            _make_task("T865"),
            _make_task("T866", status="HUMAN_REVIEW_REQUIRED"),
        ]
        report = validate_prd_task_queue(tasks, "T865", "T866")
        assert report.final_verdict == "WARN"
        forbidden = [i for i in report.issues if i.category == "forbidden_status"]
        assert len(forbidden) == 1
        assert forbidden[0].task_id == "T866"

    def test_frozen_status_warning(self):
        tasks = [
            _make_task("T865"),
            _make_task("T866", status="FROZEN"),
        ]
        report = validate_prd_task_queue(tasks, "T865", "T866")
        # FROZEN is both a valid risk_level and a valid status
        # As status it's forbidden for auto-execute
        assert report.warning_count >= 1

    def test_mixed_forbidden_and_blocker(self):
        """HUMAN_REVIEW_REQUIRED + duplicate → verdict BLOCKED (blockers win)."""
        tasks = [
            _make_task("T865", status="HUMAN_REVIEW_REQUIRED"),
            _make_task("T865", status="HUMAN_REVIEW_REQUIRED"),
        ]
        report = validate_prd_task_queue(tasks, "T865", "T865")
        assert report.final_verdict == "BLOCKED"


class TestInvalidStatus:
    """Invalid status string → BLOCKED."""

    def test_invalid_status(self):
        tasks = [_make_task("T865", status="GARBAGE")]
        report = validate_prd_task_queue(tasks, "T865", "T865")
        assert report.final_verdict == "BLOCKER" or report.final_verdict == "BLOCKED"
        inv = [i for i in report.issues if i.category == "invalid_status"]
        assert len(inv) == 1


class TestInvalidRiskLevel:
    """Invalid risk_level → BLOCKED."""

    def test_invalid_risk(self):
        tasks = [_make_task("T865", risk_level="CRITICAL")]
        report = validate_prd_task_queue(tasks, "T865", "T865")
        assert report.final_verdict == "BLOCKED"
        inv = [i for i in report.issues if i.category == "invalid_risk"]
        assert len(inv) == 1


class TestRangeOrder:
    """start > end → BLOCKED."""

    def test_inverted_range(self):
        tasks = [_make_task("T865"), _make_task("T870")]
        report = validate_prd_task_queue(tasks, "T870", "T865")
        assert report.final_verdict == "BLOCKED"
        order = [i for i in report.issues if i.category == "range_order"]
        assert len(order) == 1


class TestContiguity:
    """Gaps produce notes, not issues."""

    def test_gap_in_range(self):
        # T865, T866, T868 (missing T867)
        tasks = [_make_task("T865"), _make_task("T866"), _make_task("T868")]
        notes = validate_task_range_contiguous(tasks, "T865", "T868")
        assert len(notes) == 1
        assert "T867" in notes[0]

    def test_contiguous_no_notes(self):
        tasks = _make_range("T865", "T868")
        notes = validate_task_range_contiguous(tasks, "T865", "T868")
        assert len(notes) == 0

    def test_gaps_in_full_report(self):
        tasks = [_make_task("T865"), _make_task("T867")]
        report = validate_prd_task_queue(tasks, "T865", "T867")
        assert len(report.notes) == 1
        assert "T866" in report.notes[0]


class TestSerialization:
    """Dict and markdown serializers are deterministic."""

    def test_report_to_dict(self):
        tasks = _make_range("T865", "T866")
        report = validate_prd_task_queue(tasks, "T865", "T866")
        d = validation_report_to_dict(report)
        assert d["total_tasks"] == 2
        assert d["final_verdict"] == "PASS"
        assert isinstance(d["issues"], list)
        assert isinstance(d["notes"], list)

    def test_report_to_markdown_deterministic(self):
        tasks = _make_range("T865", "T866")
        report = validate_prd_task_queue(tasks, "T865", "T866")
        md1 = validation_report_to_markdown(report)
        md2 = validation_report_to_markdown(report)
        assert md1 == md2
        assert "PRD Task Queue Validation Report" in md1
        assert "PASS" in md1

    def test_markdown_with_issues_deterministic(self):
        tasks = [
            _make_task("T865", status="HUMAN_REVIEW_REQUIRED"),
            _make_task("T866"),
        ]
        report = validate_prd_task_queue(tasks, "T865", "T866")
        md = validation_report_to_markdown(report)
        assert "WARN" in md
        assert "HUMAN_REVIEW_REQUIRED" in md
        # Run twice — same output
        assert md == validation_report_to_markdown(report)


class TestFrozenDataclasses:
    """Dataclasses are frozen — mutation raises."""

    def test_issue_frozen(self):
        issue = PrdTaskValidationIssue(
            issue_id="X", task_id="T1", severity="blocker",
            message="m", category="c",
        )
        with pytest.raises(AttributeError):
            issue.severity = "warning"  # type: ignore[misc]

    def test_report_frozen(self):
        tasks = _make_range("T865", "T866")
        report = validate_prd_task_queue(tasks, "T865", "T866")
        with pytest.raises(AttributeError):
            report.final_verdict = "FAIL"  # type: ignore[misc]
