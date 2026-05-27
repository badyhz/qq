"""Tests for T850: runtime governance read-only final status report."""

import pytest

from core.runtime_governance_readonly_final_status_report import (
    RuntimeGovernanceReadOnlyFinalStatusReport,
    build_readonly_final_status_report,
    readonly_final_status_report_to_dict,
    readonly_final_status_report_to_markdown,
)


@pytest.fixture
def report() -> RuntimeGovernanceReadOnlyFinalStatusReport:
    return build_readonly_final_status_report()


def test_no_live_authorization_in_notes(report: RuntimeGovernanceReadOnlyFinalStatusReport) -> None:
    """Notes must explicitly state no live authorization."""
    combined = " ".join(report.notes)
    assert "no live authorization" in combined.lower() or "no live" in combined.lower()


def test_frozen_items_present(report: RuntimeGovernanceReadOnlyFinalStatusReport) -> None:
    """Frozen items must be non-empty and contain key restrictions."""
    assert len(report.frozen_items) > 0
    frozen_lower = [f.lower() for f in report.frozen_items]
    assert any("live trading" in f for f in frozen_lower)
    assert any("real execution" in f for f in frozen_lower)


def test_deterministic() -> None:
    """Two calls must produce identical reports."""
    a = build_readonly_final_status_report()
    b = build_readonly_final_status_report()
    assert a == b
    assert a is not b


def test_to_dict_has_expected_keys(report: RuntimeGovernanceReadOnlyFinalStatusReport) -> None:
    """Dict output must have all required keys."""
    d = readonly_final_status_report_to_dict(report)
    expected = {
        "task_range",
        "completed_count",
        "test_summary",
        "final_status",
        "next_safe_phase",
        "frozen_items",
        "notes",
    }
    assert set(d.keys()) == expected


def test_markdown_contains_final_status(report: RuntimeGovernanceReadOnlyFinalStatusReport) -> None:
    """Markdown output must contain the final status value."""
    md = readonly_final_status_report_to_markdown(report)
    assert report.final_status in md
    assert report.task_range in md


def test_frozen_instance() -> None:
    """Dataclass must be frozen (immutable)."""
    r = build_readonly_final_status_report()
    with pytest.raises(AttributeError):
        r.final_status = "FAIL"  # type: ignore[misc]
