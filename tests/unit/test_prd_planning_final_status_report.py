"""Tests for PRD Planning Final Status Report — T880."""

from __future__ import annotations

import pytest

from core.prd_planning_final_status_report import (
    PrdPlanningFinalStatusReport,
    build_prd_planning_final_status_report,
    planning_final_status_report_to_dict,
    planning_final_status_report_to_markdown,
)


class TestBuildPrdPlanningFinalStatusReport:
    def test_default_build(self):
        r = build_prd_planning_final_status_report()
        assert isinstance(r, PrdPlanningFinalStatusReport)
        assert r.task_range == "T873-T880"
        assert r.completed_count == 8
        assert r.final_status == "PASS"

    def test_planner_components_count(self):
        r = build_prd_planning_final_status_report()
        assert len(r.planner_components) == 8

    def test_hard_stop(self):
        r = build_prd_planning_final_status_report()
        assert r.hard_stop == "T880"

    def test_next_safe_phase_requires_human(self):
        r = build_prd_planning_final_status_report()
        assert "human" in r.next_safe_phase.lower()

    def test_deterministic_output(self):
        r1 = build_prd_planning_final_status_report()
        r2 = build_prd_planning_final_status_report()
        assert r1 == r2
        assert planning_final_status_report_to_dict(
            r1
        ) == planning_final_status_report_to_dict(r2)

    def test_frozen_dataclass(self):
        r = build_prd_planning_final_status_report()
        with pytest.raises(AttributeError):
            r.final_status = "FAIL"  # type: ignore[misc]


class TestPlanningFinalStatusReportToDict:
    def test_keys(self):
        r = build_prd_planning_final_status_report()
        d = planning_final_status_report_to_dict(r)
        expected_keys = {
            "task_range",
            "completed_count",
            "planner_components",
            "verification_summary",
            "final_status",
            "next_safe_phase",
            "hard_stop",
            "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_values(self):
        r = build_prd_planning_final_status_report()
        d = planning_final_status_report_to_dict(r)
        assert d["final_status"] == "PASS"
        assert d["completed_count"] == 8


class TestPlanningFinalStatusReportToMarkdown:
    def test_contains_header(self):
        r = build_prd_planning_final_status_report()
        md = planning_final_status_report_to_markdown(r)
        assert "# PRD Planning Final Status Report" in md

    def test_contains_pass(self):
        r = build_prd_planning_final_status_report()
        md = planning_final_status_report_to_markdown(r)
        assert "PASS" in md

    def test_contains_components(self):
        r = build_prd_planning_final_status_report()
        md = planning_final_status_report_to_markdown(r)
        assert "T873" in md
        assert "T880" in md


class TestTaskQueueDocContainsExpectedRanges:
    """Verify task queue doc has T873-T880 and T881-T900."""

    def test_doc_contains_t873_t880(self):
        import pathlib

        doc = pathlib.Path(
            "/Users/winnie/Documents/trae_projects/qq/docs/dev_prd/"
            "runtime_governance_task_queue.md"
        ).read_text()
        for t in range(873, 881):
            assert f"T{t}" in doc, f"T{t} not found in task queue doc"

    def test_doc_contains_t881_t900(self):
        import pathlib

        doc = pathlib.Path(
            "/Users/winnie/Documents/trae_projects/qq/docs/dev_prd/"
            "runtime_governance_task_queue.md"
        ).read_text()
        for t in range(881, 901):
            assert f"T{t}" in doc, f"T{t} not found in task queue doc"

    def test_t873_t880_marked_completed(self):
        import pathlib

        doc = pathlib.Path(
            "/Users/winnie/Documents/trae_projects/qq/docs/dev_prd/"
            "runtime_governance_task_queue.md"
        ).read_text()
        assert "T873-T880" in doc
        assert "completed" in doc.lower()

    def test_t881_t900_marked_human_review(self):
        import pathlib

        doc = pathlib.Path(
            "/Users/winnie/Documents/trae_projects/qq/docs/dev_prd/"
            "runtime_governance_task_queue.md"
        ).read_text()
        assert "HUMAN_REVIEW_REQUIRED" in doc
