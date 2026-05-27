"""Tests for prd_execution_report_parser."""

import pytest

from core.prd_execution_report_parser import (
    PrdExecutionReport,
    execution_report_to_dict,
    execution_report_to_markdown,
    parse_prd_execution_report,
    summarize_execution_report,
)

VALID_REPORT = """\
FILES
- core/foo.py
- core/bar.py

TESTS
- command: python3 -m pytest
- result: PASS

COMMITS
- abc1234 feat: add foo
- def5678 fix: bar

RESULT
PASS

NOTES
- no blockers
"""

VALID_REPORT_PARTIAL = """\
FILES
- core/x.py

TESTS
- command: pytest
- result: 2 passed, 1 failed

COMMITS
- 1111111 chore: wip

RESULT
PARTIAL

NOTES
- blocked on API key
"""


class TestParsePrdExecutionReport:
    def test_valid_report_parsed_ok(self):
        r = parse_prd_execution_report(VALID_REPORT)
        assert r.parsed_ok is True
        assert r.result == "PASS"
        assert r.missing_sections == []
        assert "core/foo.py" in r.files_section

    def test_missing_section_parsed_ok_false(self):
        text = """\
FILES
- x.py

RESULT
PASS
"""
        r = parse_prd_execution_report(text)
        assert r.parsed_ok is False
        assert "TESTS" in r.missing_sections
        assert "COMMITS" in r.missing_sections
        assert "NOTES" in r.missing_sections

    def test_lowercase_result_normalized(self):
        text = """\
FILES
- a.py

TESTS
- ok

COMMITS
- abc

RESULT
pass

NOTES
- ok
"""
        r = parse_prd_execution_report(text)
        assert r.result == "PASS"
        assert r.parsed_ok is True

    def test_unknown_result_parsed_ok_false(self):
        text = """\
FILES
- a.py

TESTS
- ok

COMMITS
- abc

RESULT
MAYBE

NOTES
- ok
"""
        r = parse_prd_execution_report(text)
        assert r.parsed_ok is False
        assert r.result == "MAYBE"

    def test_deterministic_output(self):
        r1 = parse_prd_execution_report(VALID_REPORT)
        r2 = parse_prd_execution_report(VALID_REPORT)
        assert r1 == r2
        assert execution_report_to_dict(r1) == execution_report_to_dict(r2)


class TestExecutionReportToDict:
    def test_keys_present(self):
        r = parse_prd_execution_report(VALID_REPORT)
        d = execution_report_to_dict(r)
        assert set(d.keys()) == {
            "files_section",
            "tests_section",
            "commits_section",
            "result",
            "notes_section",
            "missing_sections",
            "parsed_ok",
        }
        assert d["parsed_ok"] is True
        assert d["result"] == "PASS"


class TestExecutionReportToMarkdown:
    def test_contains_sections(self):
        r = parse_prd_execution_report(VALID_REPORT)
        md = execution_report_to_markdown(r)
        assert "## FILES" in md
        assert "## TESTS" in md
        assert "## COMMITS" in md
        assert "## NOTES" in md
        assert "**Result:** PASS" in md

    def test_missing_shown(self):
        text = "RESULT\nFAIL\n"
        r = parse_prd_execution_report(text)
        md = execution_report_to_markdown(r)
        assert "(missing)" in md
        assert "Missing sections" in md


class TestSummarizeExecutionReport:
    def test_summary_keys(self):
        r = parse_prd_execution_report(VALID_REPORT)
        s = summarize_execution_report(r)
        assert s["parsed_ok"] is True
        assert s["result"] == "PASS"
        assert s["has_files"] is True
        assert s["has_tests"] is True
        assert s["has_commits"] is True
        assert s["has_notes"] is True
        assert s["missing_sections"] == []
