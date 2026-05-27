"""Tests for PRD safety boundary checker — T870."""

import pytest

from core.prd_safety_boundary_checker import (
    PrdSafetyBoundaryIssue,
    PrdSafetyBoundaryReport,
    check_prd_safety_boundaries,
    safety_boundary_report_to_dict,
    safety_boundary_report_to_markdown,
)


class TestCheckPrdSafetyBoundaries:
    """Core checker tests."""

    def test_safe_prd_files_pass(self):
        """Safe docs/dev_prd files should PASS."""
        report = check_prd_safety_boundaries(
            task_text="Update PRD architecture review",
            allowed_files=[
                "docs/dev_prd/prd_pilot_architecture_review.md",
                "docs/dev_prd/prd_safety_boundary_checker.md",
                "core/prd_safety_boundary_checker.py",
            ],
        )
        assert report.final_verdict == "PASS"
        assert report.blocker_count == 0
        assert report.issue_count == 0

    def test_submit_script_path_blocked(self):
        """scripts/submit path must be BLOCKED."""
        report = check_prd_safety_boundaries(
            task_text="Implement submit logic",
            allowed_files=["scripts/submit_approved_candidates.py"],
        )
        assert report.final_verdict == "BLOCKED"
        assert report.blocker_count >= 1
        assert any(i.severity == "blocker" for i in report.issues)

    def test_env_file_blocked(self):
        """.env file must be BLOCKED."""
        report = check_prd_safety_boundaries(
            task_text="Load environment",
            allowed_files=[".env", "config.yaml"],
        )
        assert report.final_verdict == "BLOCKED"
        assert report.blocker_count >= 1

    def test_planner_path_blocked(self):
        """planner path must be BLOCKED."""
        report = check_prd_safety_boundaries(
            task_text="Check planner module",
            allowed_files=["core/planner.py"],
        )
        assert report.final_verdict == "BLOCKED"
        assert report.blocker_count >= 1

    def test_live_runner_path_blocked(self):
        report = check_prd_safety_boundaries(
            task_text="refactor",
            allowed_files=["core/live_runner.py"],
        )
        assert report.final_verdict == "BLOCKED"

    def test_exchange_client_path_blocked(self):
        report = check_prd_safety_boundaries(
            task_text="update client",
            allowed_files=["core/exchange_client.py"],
        )
        assert report.final_verdict == "BLOCKED"

    def test_credentials_path_blocked(self):
        report = check_prd_safety_boundaries(
            task_text="fix creds",
            allowed_files=["config/credentials.json"],
        )
        assert report.final_verdict == "BLOCKED"

    def test_forbidden_term_with_negation_context_warning(self):
        """Task text mentioning forbidden term with 'do not' context → warning, not blocker."""
        report = check_prd_safety_boundaries(
            task_text="This PRD does not allow live trading in pilot phase",
            allowed_files=["docs/dev_prd/pilot.md"],
        )
        assert report.final_verdict == "WARN"
        assert report.blocker_count == 0
        assert report.issue_count >= 1
        assert any(i.severity == "warning" for i in report.issues)

    def test_forbidden_term_without_negation_blocked(self):
        """Task text with forbidden term but no negation context → blocker."""
        report = check_prd_safety_boundaries(
            task_text="Enable live trading for pilot",
            allowed_files=["docs/dev_prd/pilot.md"],
        )
        assert report.final_verdict == "BLOCKED"
        assert report.blocker_count >= 1

    def test_frozen_context_suppresses_blocker(self):
        report = check_prd_safety_boundaries(
            task_text="Secrets management is frozen — do not modify",
            allowed_files=["docs/dev_prd/secrets_note.md"],
        )
        # .md path doesn't match blocked substrings; term 'secret' with negation → WARN at most
        # The file path "secrets_note.md" contains "secrets" → BLOCKER from path check
        assert report.final_verdict == "BLOCKED"  # path-level block still applies

    def test_deterministic_output(self):
        """Same inputs must produce identical reports."""
        args = ("Submit live trading plan", ["scripts/submit.py"])
        r1 = check_prd_safety_boundaries(*args)
        r2 = check_prd_safety_boundaries(*args)
        assert r1 == r2
        assert r1.issues == r2.issues

    def test_empty_inputs(self):
        report = check_prd_safety_boundaries(task_text="", allowed_files=[])
        assert report.final_verdict == "PASS"
        assert report.checked_items == 1  # task_text counts as 1
        assert report.issue_count == 0


class TestReportToDict:
    def test_basic_structure(self):
        report = check_prd_safety_boundaries("safe", ["docs/dev_prd/a.md"])
        d = safety_boundary_report_to_dict(report)
        assert d["final_verdict"] == "PASS"
        assert isinstance(d["issues"], list)
        assert "checked_items" in d


class TestReportToMarkdown:
    def test_contains_verdict(self):
        report = check_prd_safety_boundaries("safe", ["docs/dev_prd/a.md"])
        md = safety_boundary_report_to_markdown(report)
        assert "PASS" in md
        assert "PRD Safety Boundary Report" in md

    def test_blocked_report_has_table(self):
        report = check_prd_safety_boundaries(
            "Enable live trading", ["scripts/submit.py"]
        )
        md = safety_boundary_report_to_markdown(report)
        assert "BLOCKED" in md
        assert "Severity" in md


class TestDataclassFrozen:
    def test_issue_frozen(self):
        issue = PrdSafetyBoundaryIssue(
            issue_id="T1", severity="blocker", category="test",
            target="x", message="m",
        )
        with pytest.raises(AttributeError):
            issue.issue_id = "T2"  # type: ignore[misc]

    def test_report_frozen(self):
        report = PrdSafetyBoundaryReport(
            checked_items=1, issue_count=0, blocker_count=0,
            final_verdict="PASS", issues=(), notes=(),
        )
        with pytest.raises(AttributeError):
            report.final_verdict = "FAIL"  # type: ignore[misc]
