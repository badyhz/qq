"""T792 — Governance failure verdict matrix tests."""

import pytest
from core.governance_failure_verdict_matrix import (
    GovernanceVerdictCase,
    resolve_governance_final_verdict,
    build_governance_verdict_matrix,
    verdict_matrix_to_dict,
    verdict_matrix_to_markdown,
)


# ── resolve rules ────────────────────────────────────────────────────


def test_pass_snapshot_ok():
    assert resolve_governance_final_verdict("PASS", True) == "PASS"


def test_warn_snapshot_ok():
    assert resolve_governance_final_verdict("WARN", True) == "WARN"


def test_fail_snapshot_ok():
    assert resolve_governance_final_verdict("FAIL", True) == "FAIL"


def test_blocked_snapshot_ok():
    assert resolve_governance_final_verdict("BLOCKED", True) == "BLOCKED"


def test_pass_snapshot_not_ok():
    assert resolve_governance_final_verdict("PASS", False) == "FAIL"


def test_warn_snapshot_not_ok():
    assert resolve_governance_final_verdict("WARN", False) == "FAIL"


def test_fail_snapshot_not_ok():
    assert resolve_governance_final_verdict("FAIL", False) == "FAIL"


def test_blocked_snapshot_not_ok():
    assert resolve_governance_final_verdict("BLOCKED", False) == "BLOCKED"


def test_unknown_report_verdict():
    assert resolve_governance_final_verdict("UNKNOWN", False) == "FAIL"
    assert resolve_governance_final_verdict("GIBBERISH", True) == "FAIL"


# ── matrix ───────────────────────────────────────────────────────────


def test_matrix_has_9_cases():
    matrix = build_governance_verdict_matrix()
    assert len(matrix) == 9


def test_matrix_covers_all_rules():
    matrix = build_governance_verdict_matrix()
    for case in matrix:
        result = resolve_governance_final_verdict(case.report_verdict, case.snapshot_ok)
        assert result == case.expected_final_verdict, f"{case}"


def test_matrix_ordering_stable():
    m1 = build_governance_verdict_matrix()
    m2 = build_governance_verdict_matrix()
    assert len(m1) == len(m2)
    for a, b in zip(m1, m2):
        assert a.report_verdict == b.report_verdict
        assert a.snapshot_ok == b.snapshot_ok


# ── dict serialization ───────────────────────────────────────────────


def test_dict_serialization():
    matrix = build_governance_verdict_matrix()
    dicts = verdict_matrix_to_dict(matrix)
    assert len(dicts) == 9
    assert dicts[0]["report_verdict"] == "PASS"
    assert dicts[0]["snapshot_ok"] is True
    assert dicts[0]["expected_final_verdict"] == "PASS"


def test_dict_keys():
    dicts = verdict_matrix_to_dict(build_governance_verdict_matrix())
    for d in dicts:
        assert set(d.keys()) == {"report_verdict", "snapshot_ok", "expected_final_verdict", "reason"}


# ── markdown ─────────────────────────────────────────────────────────


def test_markdown_contains_table():
    md = verdict_matrix_to_markdown(build_governance_verdict_matrix())
    assert "| Report Verdict | Snapshot OK | Final Verdict | Reason |" in md
    assert "|---" in md


def test_markdown_deterministic():
    matrix = build_governance_verdict_matrix()
    md1 = verdict_matrix_to_markdown(matrix)
    md2 = verdict_matrix_to_markdown(matrix)
    assert md1 == md2


def test_markdown_no_timestamps():
    md = verdict_matrix_to_markdown(build_governance_verdict_matrix())
    assert "2026" not in md
    assert "2025" not in md
