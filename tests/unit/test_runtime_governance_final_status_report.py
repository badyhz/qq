import pytest
from core.runtime_governance_final_status_report import (
    RuntimeGovernanceFinalStatusReport,
    build_runtime_governance_final_status_report,
    final_status_report_to_dict,
    final_status_report_to_markdown,
)


class TestBuildReport:
    def test_returns_frozen_dataclass(self):
        report = build_runtime_governance_final_status_report()
        assert isinstance(report, RuntimeGovernanceFinalStatusReport)
        assert report.final_status == "PASS"

    def test_completed_task_count(self):
        report = build_runtime_governance_final_status_report()
        assert report.completed_task_count == 28
        assert report.committed_task_count == 28

    def test_no_live_trading_recommendation(self):
        report = build_runtime_governance_final_status_report()
        phase = report.next_recommended_phase.lower()
        assert "live trading" not in phase
        assert "live" not in phase.split()

    def test_frozen_items_include_critical_blocks(self):
        report = build_runtime_governance_final_status_report()
        frozen = report.frozen_items
        assert "live submit" in frozen
        assert "secrets access" in frozen
        assert "planner autonomous integration" in frozen

    def test_risk_summary_blocks_live(self):
        report = build_runtime_governance_final_status_report()
        assert report.risk_summary["live_trading_blocked"] is True
        assert report.risk_summary["secrets_access_blocked"] is True
        assert report.risk_summary["dry_run_default"] is True


class TestToDict:
    def test_deterministic(self):
        report = build_runtime_governance_final_status_report()
        d1 = final_status_report_to_dict(report)
        d2 = final_status_report_to_dict(report)
        assert d1 == d2

    def test_keys(self):
        report = build_runtime_governance_final_status_report()
        d = final_status_report_to_dict(report)
        expected_keys = {
            "completed_task_count",
            "committed_task_count",
            "test_summary",
            "risk_summary",
            "final_status",
            "next_recommended_phase",
            "frozen_items",
            "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_no_live_in_next_phase(self):
        report = build_runtime_governance_final_status_report()
        d = final_status_report_to_dict(report)
        assert "live" not in d["next_recommended_phase"].lower().split()


class TestToMarkdown:
    def test_deterministic(self):
        report = build_runtime_governance_final_status_report()
        md1 = final_status_report_to_markdown(report)
        md2 = final_status_report_to_markdown(report)
        assert md1 == md2

    def test_contains_header(self):
        report = build_runtime_governance_final_status_report()
        md = final_status_report_to_markdown(report)
        assert "# Runtime Governance Final Status Report" in md

    def test_no_live_trading_in_markdown(self):
        report = build_runtime_governance_final_status_report()
        md = final_status_report_to_markdown(report)
        phase_line = [
            line for line in md.splitlines()
            if "Next phase" in line
        ][0]
        assert "live trading" not in phase_line.lower()

    def test_frozen_items_present(self):
        report = build_runtime_governance_final_status_report()
        md = final_status_report_to_markdown(report)
        assert "- live submit" in md
        assert "- secrets access" in md
        assert "- planner autonomous integration" in md
        assert "- real exchange execution" in md
