"""Tests for PRD dependency graph validator — T877."""

from typing import List, Optional

import pytest

from core.prd_backlog_schema import PrdBacklogItem
from core.prd_dependency_graph_validator import (
    PrdDependencyIssue,
    PrdDependencyValidationReport,
    dependency_report_to_dict,
    dependency_report_to_markdown,
    detect_dependency_cycles,
    detect_missing_dependencies,
    validate_prd_dependency_graph,
)


def _item(task_id: str, deps: Optional[List[str]] = None) -> PrdBacklogItem:
    """Factory for test items."""
    return PrdBacklogItem(
        task_id=task_id,
        title=f"Task {task_id}",
        milestone_id="M1",
        wave_id="W1",
        batch_id="B1",
        risk_level="low",
        status="pending",
        dependencies=deps or [],
        allowed_file_patterns=[],
        forbidden_file_patterns=[],
        acceptance_command_ids=[],
        notes=[],
    )


class TestDetectMissingDependencies:
    def test_no_missing(self) -> None:
        items = [_item("T1"), _item("T2", ["T1"])]
        assert detect_missing_dependencies(items) == []

    def test_missing_found(self) -> None:
        items = [_item("T1", ["T99"])]
        issues = detect_missing_dependencies(items)
        assert len(issues) == 1
        assert issues[0].severity == "blocker"
        assert issues[0].dependency_id == "T99"


class TestDetectDependencyCycles:
    def test_no_cycle(self) -> None:
        items = [_item("T1"), _item("T2", ["T1"]), _item("T3", ["T2"])]
        assert detect_dependency_cycles(items) == []

    def test_simple_cycle(self) -> None:
        items = [_item("T1", ["T2"]), _item("T2", ["T1"])]
        issues = detect_dependency_cycles(items)
        assert len(issues) == 2
        assert all(i.severity == "fail" for i in issues)
        ids = {i.task_id for i in issues}
        assert ids == {"T1", "T2"}

    def test_self_reference_cycle(self) -> None:
        items = [_item("T1", ["T1"])]
        issues = detect_dependency_cycles(items)
        assert len(issues) == 1
        assert issues[0].task_id == "T1"


class TestValidatePrdDependencyGraph:
    def test_valid_graph_pass(self) -> None:
        items = [_item("T1"), _item("T2", ["T1"]), _item("T3", ["T2"])]
        report = validate_prd_dependency_graph(items)
        assert report.final_verdict == "PASS"
        assert report.issue_count == 0
        assert report.cycle_count == 0
        assert report.missing_dependency_count == 0

    def test_missing_dependency_blocked(self) -> None:
        items = [_item("T1", ["T99"])]
        report = validate_prd_dependency_graph(items)
        assert report.final_verdict == "BLOCKED"
        assert report.missing_dependency_count == 1

    def test_simple_cycle_fail(self) -> None:
        items = [_item("T1", ["T2"]), _item("T2", ["T1"])]
        report = validate_prd_dependency_graph(items)
        assert report.final_verdict == "FAIL"
        assert report.cycle_count == 2

    def test_future_dependency_warn(self) -> None:
        items = [_item("T1", ["T2"]), _item("T2")]
        report = validate_prd_dependency_graph(items)
        assert report.final_verdict == "WARN"
        assert report.issue_count >= 1
        assert all(i.severity == "warning" for i in report.issues)

    def test_deterministic_report(self) -> None:
        items = [_item("T1"), _item("T2", ["T1"])]
        r1 = validate_prd_dependency_graph(items)
        r2 = validate_prd_dependency_graph(items)
        assert dependency_report_to_dict(r1) == dependency_report_to_dict(r2)


class TestSerializers:
    def test_report_to_dict(self) -> None:
        items = [_item("T1"), _item("T2", ["T1"])]
        report = validate_prd_dependency_graph(items)
        d = dependency_report_to_dict(report)
        assert d["final_verdict"] == "PASS"
        assert d["task_count"] == 2
        assert isinstance(d["issues"], list)
        assert isinstance(d["notes"], list)

    def test_report_to_markdown(self) -> None:
        items = [_item("T1", ["T99"])]
        report = validate_prd_dependency_graph(items)
        md = dependency_report_to_markdown(report)
        assert "BLOCKED" in md
        assert "T1" in md
        assert "Missing deps" in md or "missing" in md.lower()
