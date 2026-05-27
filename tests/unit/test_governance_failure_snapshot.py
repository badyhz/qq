"""T788 — Governance failure snapshot verifier tests."""

import pytest
from core.governance_failure_snapshot import (
    GovernanceFailureSnapshotDiff,
    normalize_governance_failure_markdown,
    compare_governance_failure_markdown,
)


def test_equal_markdown_ok():
    md = "# Report\n\n**Verdict:** PASS\n\n## By Category\n\ntext\n"
    diff = compare_governance_failure_markdown(md, md)
    assert diff.ok is True
    assert diff.expected_hash == diff.actual_hash
    assert diff.changed_sections == []
    assert diff.added_lines == []
    assert diff.removed_lines == []


def test_changed_markdown_not_ok():
    md1 = "# Report\n\n**Verdict:** PASS\n"
    md2 = "# Report\n\n**Verdict:** FAIL\n"
    diff = compare_governance_failure_markdown(md1, md2)
    assert diff.ok is False
    assert diff.expected_hash != diff.actual_hash


def test_changed_sections_detected():
    md1 = "# Report\n\n## By Category\n\ncat1\n\n## By Severity\n\nsev1\n"
    md2 = "# Report\n\n## By Category\n\ncat2\n\n## By Severity\n\nsev1\n"
    diff = compare_governance_failure_markdown(md1, md2)
    assert diff.ok is False
    assert "By Category" in diff.changed_sections
    assert "By Severity" not in diff.changed_sections


def test_added_lines_detected():
    md1 = "# Report\n\nline1\n"
    md2 = "# Report\n\nline1\n\nline2\n"
    diff = compare_governance_failure_markdown(md1, md2)
    assert diff.ok is False
    assert "line2" in diff.added_lines


def test_removed_lines_detected():
    md1 = "# Report\n\nline1\n\nline2\n"
    md2 = "# Report\n\nline1\n"
    diff = compare_governance_failure_markdown(md1, md2)
    assert diff.ok is False
    assert "line2" in diff.removed_lines


def test_hash_deterministic():
    md = "# Report\n\n**Verdict:** PASS\n"
    d1 = compare_governance_failure_markdown(md, md)
    d2 = compare_governance_failure_markdown(md, md)
    assert d1.expected_hash == d2.expected_hash
    assert d1.actual_hash == d2.actual_hash


def test_normalize_strips_trailing_whitespace():
    raw = "# Report   \n\n**Verdict:** PASS   \n\n\n\n"
    norm = normalize_governance_failure_markdown(raw)
    assert norm == "# Report\n\n**Verdict:** PASS"
    assert "   " not in norm


def test_normalize_collapses_blank_lines():
    raw = "# Report\n\n\n\n\n**Verdict:** PASS\n"
    norm = normalize_governance_failure_markdown(raw)
    assert "\n\n\n" not in norm


def test_normalize_strips_leading_trailing_blanks():
    raw = "\n\n# Report\n\n**Verdict:** PASS\n\n\n"
    norm = normalize_governance_failure_markdown(raw)
    assert not norm.startswith("\n")
    assert not norm.endswith("\n\n")


def test_equal_after_normalization():
    raw1 = "# Report  \n\n\n**Verdict:** PASS   \n"
    raw2 = "# Report\n\n**Verdict:** PASS\n"
    diff = compare_governance_failure_markdown(raw1, raw2)
    assert diff.ok is True


def test_empty_markdown_equal():
    diff = compare_governance_failure_markdown("", "")
    assert diff.ok is True


def test_empty_vs_content():
    diff = compare_governance_failure_markdown("", "# Report\n")
    assert diff.ok is False
