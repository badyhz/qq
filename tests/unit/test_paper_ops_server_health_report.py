"""Unit test: paper ops server health report."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_deployment.server_health_report import generate_health_report


def test_health_report_generates() -> None:
    report = generate_health_report()
    assert report.health_score >= 0
    assert report.health_score <= 100


def test_health_status() -> None:
    report = generate_health_report()
    assert report.health_status in ("HEALTHY", "DEGRADED", "UNHEALTHY")


def test_health_verdict_format() -> None:
    report = generate_health_report()
    assert "PAPER_OPS_SERVER_HEALTH_REPORT_READY" in report.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in report.final_verdict


def test_health_to_dict() -> None:
    report = generate_health_report()
    d = report.to_dict()
    assert "health_id" in d
    assert "health_score" in d


def test_health_has_actions() -> None:
    report = generate_health_report()
    assert len(report.recommended_actions) > 0


def main() -> None:
    test_health_report_generates()
    test_health_status()
    test_health_verdict_format()
    test_health_to_dict()
    test_health_has_actions()
    print("test_paper_ops_server_health_report: ALL PASS")


if __name__ == "__main__":
    main()
