"""Integration test: mock review closeout summary."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_closeout.closeout_summary import create_summary


def test_create_summary():
    summary = create_summary()
    assert len(summary.stages) == 5
    assert summary.overall_status == "MOCK_REVIEW_CLOSEOUT_READY"


def test_stages_cover_milestones():
    summary = create_summary()
    milestones = {s.milestone for s in summary.stages}
    assert "T140001-T155000" in milestones
    assert "T155001-T170000" in milestones
    assert "T170001-T185000" in milestones
    assert "T185001-T200000" in milestones
    assert "T200001-T215000" in milestones


def test_all_stages_complete():
    summary = create_summary()
    for s in summary.stages:
        assert s.status == "COMPLETE"


def test_render_report_markers():
    summary = create_summary()
    report = summary.__class__.__module__  # just check module loads
    from src.runtime_integrations.testnet_mock_closeout.closeout_summary import render_report
    report = render_report(summary)
    assert "MOCK_REVIEW_CLOSEOUT_READY" in report
    assert "REAL_TRADING_NOT_ALLOWED" in report
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in report
