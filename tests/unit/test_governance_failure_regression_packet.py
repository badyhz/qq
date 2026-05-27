"""T789 — Governance failure regression packet tests."""

import pytest
from core.governance_failure_taxonomy import (
    FailureCategory, FailureSeverity, GovernanceFailure,
    classify_governance_failure,
)
from core.governance_failure_report import build_governance_failure_report, report_to_markdown
from core.governance_failure_regression_packet import (
    GovernanceFailureRegressionPacket,
    build_governance_failure_regression_packet,
    packet_to_dict,
    packet_to_markdown,
)


# ── final verdict ────────────────────────────────────────────────────


def test_packet_pass_when_no_failures():
    pkt = build_governance_failure_regression_packet([])
    assert pkt.final_verdict == "PASS"
    assert pkt.report_summary["verdict"] == "PASS"
    assert pkt.snapshot_diff.ok is True


def test_packet_warn():
    failures = [classify_governance_failure(status_code=429)]
    pkt = build_governance_failure_regression_packet(failures)
    assert pkt.final_verdict == "WARN"


def test_packet_fail_on_error():
    failures = [classify_governance_failure(status_code=403)]
    pkt = build_governance_failure_regression_packet(failures)
    assert pkt.final_verdict == "FAIL"


def test_packet_blocked_on_critical_non_retryable():
    failures = [
        GovernanceFailure(
            category=FailureCategory.POLICY_BLOCK,
            severity=FailureSeverity.CRITICAL,
            code="PB", message="hard block", retryable=False,
        ),
    ]
    pkt = build_governance_failure_regression_packet(failures)
    assert pkt.final_verdict == "BLOCKED"


def test_packet_fail_when_snapshot_mismatch():
    expected_md = "# Report\n\n**Verdict:** PASS\n"
    failures = [classify_governance_failure(status_code=429)]
    pkt = build_governance_failure_regression_packet(
        failures, expected_markdown=expected_md,
    )
    assert pkt.snapshot_diff.ok is False
    assert pkt.final_verdict == "FAIL"


def test_packet_blocked_when_report_blocked_and_snapshot_mismatch():
    expected_md = "# Report\n\n**Verdict:** PASS\n"
    failures = [
        GovernanceFailure(
            category=FailureCategory.POLICY_BLOCK,
            severity=FailureSeverity.CRITICAL,
            code="PB", message="hard block", retryable=False,
        ),
    ]
    pkt = build_governance_failure_regression_packet(
        failures, expected_markdown=expected_md,
    )
    assert pkt.final_verdict == "BLOCKED"


# ── snapshot integration ─────────────────────────────────────────────


def test_packet_snapshot_ok_when_markdown_matches():
    failures = [classify_governance_failure(status_code=429)]
    title = "Governance Failure Regression"
    report = build_governance_failure_report(failures, title=title)
    expected_md = report_to_markdown(report)
    pkt = build_governance_failure_regression_packet(
        failures, title=title, expected_markdown=expected_md,
    )
    assert pkt.snapshot_diff.ok is True
    assert pkt.final_verdict == "WARN"


# ── dict serialization ───────────────────────────────────────────────


def test_packet_to_dict_keys():
    pkt = build_governance_failure_regression_packet([], notes=["n1"])
    d = packet_to_dict(pkt)
    assert "report" in d
    assert "snapshot_diff" in d
    assert "report_summary" in d
    assert "snapshot_summary" in d
    assert "final_verdict" in d
    assert d["notes"] == ["n1"]


def test_packet_to_dict_snapshot_diff_structure():
    pkt = build_governance_failure_regression_packet([])
    d = packet_to_dict(pkt)
    sd = d["snapshot_diff"]
    assert sd["ok"] is True
    assert "expected_hash" in sd
    assert "actual_hash" in sd
    assert isinstance(sd["changed_sections"], list)


# ── markdown ─────────────────────────────────────────────────────────


def test_packet_markdown_contains_verdict():
    pkt = build_governance_failure_regression_packet([])
    md = packet_to_markdown(pkt)
    assert "**Final Verdict:** PASS" in md
    assert "**Report Verdict:** PASS" in md
    assert "**Snapshot OK:** True" in md


def test_packet_markdown_has_sections():
    failures = [classify_governance_failure(status_code=429, source="adapter")]
    pkt = build_governance_failure_regression_packet(failures)
    md = packet_to_markdown(pkt)
    assert "## Snapshot Diff" in md
    assert "## Report Summary" in md
    assert "## By Category" in md
    assert "## By Severity" in md


def test_packet_markdown_deterministic():
    failures = [classify_governance_failure(status_code=429)]
    pkt = build_governance_failure_regression_packet(failures)
    md1 = packet_to_markdown(pkt)
    md2 = packet_to_markdown(pkt)
    assert md1 == md2


def test_packet_markdown_sorted_categories():
    failures = [
        classify_governance_failure(status_code=403),
        classify_governance_failure(status_code=429),
    ]
    pkt = build_governance_failure_regression_packet(failures)
    md = packet_to_markdown(pkt)
    idx_rate = md.index("rate_limit")
    idx_sandbox = md.index("sandbox_block")
    assert idx_rate < idx_sandbox


def test_packet_markdown_notes():
    pkt = build_governance_failure_regression_packet([], notes=["note a", "note b"])
    md = packet_to_markdown(pkt)
    assert "- note a" in md
    assert "- note b" in md


def test_packet_markdown_snapshot_mismatch_details():
    expected_md = "# Report\n\n**Verdict:** PASS\n"
    failures = [classify_governance_failure(status_code=429)]
    pkt = build_governance_failure_regression_packet(
        failures, expected_markdown=expected_md,
    )
    md = packet_to_markdown(pkt)
    assert "**Snapshot OK:** False" in md
    assert "Changed sections" in md
