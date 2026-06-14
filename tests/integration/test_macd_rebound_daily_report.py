"""Integration test: MACD rebound daily report."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.external_scanner_integrations.macd_rebound_daily_report import generate_daily_report, render_report

FIXTURE = str(pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "macd_rebound_scanner")


def test_daily_report_status() -> None:
    report = generate_daily_report(FIXTURE)
    assert report.scanner_status in ("HEALTHY", "DEGRADED")


def test_daily_report_health_score() -> None:
    report = generate_daily_report(FIXTURE)
    assert 0 <= report.health_score <= 100


def test_daily_report_signals() -> None:
    report = generate_daily_report(FIXTURE)
    assert report.total_signals == 3


def test_daily_report_anomalies() -> None:
    report = generate_daily_report(FIXTURE)
    assert len(report.anomaly_summary) > 0


def test_daily_report_actions() -> None:
    report = generate_daily_report(FIXTURE)
    assert len(report.suggested_actions) > 0


def test_daily_report_verdict() -> None:
    report = generate_daily_report(FIXTURE)
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in report.final_verdict


def test_render_report() -> None:
    report = generate_daily_report(FIXTURE)
    md = render_report(report)
    assert "# MACD Rebound Daily Report" in md


def main() -> None:
    test_daily_report_status()
    test_daily_report_health_score()
    test_daily_report_signals()
    test_daily_report_anomalies()
    test_daily_report_actions()
    test_daily_report_verdict()
    test_render_report()
    print("test_macd_rebound_daily_report: ALL PASS")


if __name__ == "__main__":
    main()
