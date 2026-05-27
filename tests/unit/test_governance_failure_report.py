"""T787 — Governance failure report builder tests."""

import pytest
from core.governance_failure_taxonomy import (
    FailureCategory, FailureSeverity, GovernanceFailure,
    classify_governance_failure,
)
from core.governance_failure_report import (
    GovernanceFailureReport,
    build_governance_failure_report,
    report_to_dict,
    report_to_markdown,
)


# ── verdict rules ────────────────────────────────────────────────────


def test_empty_failures_pass():
    r = build_governance_failure_report([])
    assert r.verdict == "PASS"
    assert r.total_failures == 0


def test_warning_only_gives_warn():
    failures = [classify_governance_failure(status_code=429)]
    r = build_governance_failure_report(failures)
    assert r.verdict == "WARN"


def test_error_gives_fail():
    failures = [classify_governance_failure(status_code=403)]
    r = build_governance_failure_report(failures)
    assert r.verdict == "FAIL"


def test_critical_non_retryable_gives_blocked():
    failures = [
        GovernanceFailure(
            category=FailureCategory.POLICY_BLOCK,
            severity=FailureSeverity.CRITICAL,
            code="POLICY_BLOCK",
            message="hard block",
            retryable=False,
        ),
    ]
    r = build_governance_failure_report(failures)
    assert r.verdict == "BLOCKED"


def test_critical_retryable_gives_fail_not_blocked():
    failures = [
        GovernanceFailure(
            category=FailureCategory.TIMEOUT,
            severity=FailureSeverity.CRITICAL,
            code="TIMEOUT",
            message="critical timeout",
            retryable=True,
        ),
    ]
    r = build_governance_failure_report(failures)
    assert r.verdict == "FAIL"


# ── counts ───────────────────────────────────────────────────────────


def test_category_counts():
    failures = [
        classify_governance_failure(status_code=429),
        classify_governance_failure(status_code=429),
        classify_governance_failure(status_code=403),
    ]
    r = build_governance_failure_report(failures)
    assert r.by_category["rate_limit"] == 2
    assert r.by_category["sandbox_block"] == 1


def test_severity_counts():
    failures = [
        classify_governance_failure(status_code=429),  # WARNING
        classify_governance_failure(status_code=403),  # ERROR
    ]
    r = build_governance_failure_report(failures)
    assert r.by_severity["warning"] == 1
    assert r.by_severity["error"] == 1


def test_retryable_non_retryable_counts():
    failures = [
        classify_governance_failure(status_code=429),  # retryable
        classify_governance_failure(status_code=403),  # non-retryable
    ]
    r = build_governance_failure_report(failures)
    assert r.retryable_count == 1
    assert r.non_retryable_count == 1


def test_critical_count():
    failures = [
        GovernanceFailure(
            category=FailureCategory.POLICY_BLOCK,
            severity=FailureSeverity.CRITICAL,
            code="PB", message="x", retryable=False,
        ),
        classify_governance_failure(status_code=429),
    ]
    r = build_governance_failure_report(failures)
    assert r.critical_count == 1


# ── top sources ──────────────────────────────────────────────────────


def test_top_sources_sorted():
    failures = [
        classify_governance_failure(source="alpha"),
        classify_governance_failure(source="beta"),
        classify_governance_failure(source="beta"),
        classify_governance_failure(source="alpha"),
        classify_governance_failure(source="alpha"),
    ]
    r = build_governance_failure_report(failures)
    assert r.top_sources == [("alpha", 3), ("beta", 2)]


def test_top_sources_empty_source_excluded():
    failures = [
        classify_governance_failure(source=""),
        classify_governance_failure(source="adapter"),
    ]
    r = build_governance_failure_report(failures)
    assert len(r.top_sources) == 1
    assert r.top_sources[0] == ("adapter", 1)


# ── dict serialization ───────────────────────────────────────────────


def test_report_to_dict_keys():
    r = build_governance_failure_report([], title="Test", notes=["note1"])
    d = report_to_dict(r)
    assert d["title"] == "Test"
    assert d["total_failures"] == 0
    assert d["verdict"] == "PASS"
    assert d["notes"] == ["note1"]
    assert isinstance(d["by_category"], dict)
    assert isinstance(d["top_sources"], list)


def test_report_to_dict_sorted_categories():
    failures = [
        classify_governance_failure(status_code=403),
        classify_governance_failure(status_code=429),
    ]
    d = report_to_dict(build_governance_failure_report(failures))
    cats = list(d["by_category"].keys())
    assert cats == sorted(cats)


# ── markdown ─────────────────────────────────────────────────────────


def test_markdown_contains_title():
    r = build_governance_failure_report([], title="My Report")
    md = report_to_markdown(r)
    assert "# My Report" in md


def test_markdown_contains_verdict():
    r = build_governance_failure_report([])
    md = report_to_markdown(r)
    assert "**Verdict:** PASS" in md


def test_markdown_has_sections():
    failures = [
        classify_governance_failure(status_code=429, source="adapter", message="rate limited"),
    ]
    md = report_to_markdown(build_governance_failure_report(failures))
    assert "## By Category" in md
    assert "## By Severity" in md
    assert "## Top Sources" in md
    assert "## Failures" in md


def test_markdown_deterministic():
    failures = [
        classify_governance_failure(status_code=429, source="a"),
        classify_governance_failure(status_code=403, source="b"),
    ]
    r = build_governance_failure_report(failures)
    md1 = report_to_markdown(r)
    md2 = report_to_markdown(r)
    assert md1 == md2


def test_markdown_sorted_categories():
    failures = [
        classify_governance_failure(status_code=403),
        classify_governance_failure(status_code=429),
    ]
    md = report_to_markdown(build_governance_failure_report(failures))
    idx_sandbox = md.index("sandbox_block")
    idx_rate = md.index("rate_limit")
    assert idx_rate < idx_sandbox  # alphabetically sorted


def test_markdown_notes():
    r = build_governance_failure_report([], notes=["note a", "note b"])
    md = report_to_markdown(r)
    assert "- note a" in md
    assert "- note b" in md


def test_markdown_empty_no_crash():
    md = report_to_markdown(build_governance_failure_report([]))
    assert "PASS" in md
