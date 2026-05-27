"""Tests for PRD 500 backlog validator — T904.

Pure deterministic. No I/O. No timestamps. No random.
"""

from typing import List, Optional

import pytest

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem
from core.prd_500_backlog_validator import (
    Prd500BacklogValidationIssue,
    Prd500BacklogValidationReport,
    validate_prd_500_backlog,
    validation_report_to_dict,
    validation_report_to_markdown,
)


# --- Helpers ---


def _make_item(
    task_id: str = "T001",
    title: str = "task",
    risk_level: str = "LOW",
    status: str = "NOT_STARTED",
    forbidden_file_patterns: Optional[list] = None,
    notes: Optional[list] = None,
    allowed_file_patterns: Optional[list] = None,
) -> PrdBacklogItem:
    return PrdBacklogItem(
        task_id=task_id,
        title=title,
        milestone_id="M1",
        wave_id="W1",
        batch_id="B1",
        risk_level=risk_level,
        status=status,
        dependencies=[],
        allowed_file_patterns=allowed_file_patterns if allowed_file_patterns is not None else ["core/*.py"],
        forbidden_file_patterns=forbidden_file_patterns if forbidden_file_patterns is not None else [".env", "secrets"],
        acceptance_command_ids=["pytest"],
        notes=notes if notes is not None else [],
    )


def _make_backlog(items: list, backlog_id: str = "BL-TEST") -> PrdBacklog:
    return PrdBacklog(
        backlog_id=backlog_id,
        items=items,
        total_expected_tasks=len(items),
        status="ACTIVE",
        notes=[],
    )


def _make_500_backlog(
    base_task_id_prefix: str = "T",
    risk_level: str = "LOW",
    status: str = "NOT_STARTED",
) -> PrdBacklog:
    items = [
        _make_item(
            task_id=f"{base_task_id_prefix}{i:04d}",
            title=f"task {i}",
            risk_level=risk_level,
            status=status,
        )
        for i in range(500)
    ]
    return _make_backlog(items)


# --- Tests ---


class TestValidator:
    def test_default_pass_or_warn(self):
        backlog = _make_500_backlog()
        report = validate_prd_500_backlog(backlog)
        assert report.final_verdict in {"PASS", "WARN"}

    def test_less_than_500_fail(self):
        items = [_make_item(task_id=f"T{i:04d}") for i in range(10)]
        backlog = _make_backlog(items)
        report = validate_prd_500_backlog(backlog)
        assert report.final_verdict == "FAIL"
        assert any(i.category == "count" for i in report.issues)

    def test_duplicate_fail(self):
        items = [_make_item(task_id="T0001") for _ in range(500)]
        backlog = _make_backlog(items)
        report = validate_prd_500_backlog(backlog)
        assert report.final_verdict == "FAIL"
        assert any(i.category == "duplicate" for i in report.issues)

    def test_frozen_executable_blocked(self):
        items = [_make_item(task_id=f"T{i:04d}") for i in range(500)]
        items.append(_make_item(task_id="T-FROZEN", risk_level="FROZEN", status="NOT_STARTED"))
        backlog = _make_backlog(items)
        report = validate_prd_500_backlog(backlog)
        assert report.final_verdict == "BLOCKED"
        assert any(i.category == "frozen_executable" for i in report.issues)

    def test_deterministic_markdown(self):
        backlog = _make_500_backlog()
        report = validate_prd_500_backlog(backlog)
        md1 = validation_report_to_markdown(report)
        md2 = validation_report_to_markdown(report)
        assert md1 == md2
        assert "# PRD 500 Backlog Validation Report" in md1
        assert "**Verdict:**" in md1

    def test_report_to_dict_keys(self):
        backlog = _make_500_backlog()
        report = validate_prd_500_backlog(backlog)
        d = validation_report_to_dict(report)
        assert set(d.keys()) == {
            "total_items", "issue_count", "blocker_count",
            "warning_count", "final_verdict", "issues", "notes",
        }

    def test_high_risk_warn(self):
        items = [_make_item(task_id=f"T{i:04d}") for i in range(500)]
        items[0] = _make_item(task_id="T0000", risk_level="HIGH", status="NOT_STARTED")
        backlog = _make_backlog(items)
        report = validate_prd_500_backlog(backlog)
        assert report.final_verdict in {"WARN", "BLOCKED"}
        assert report.warning_count >= 1
