"""Integration test: MACD rebound health check."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.external_scanner_integrations.macd_rebound_health import run_health_check, render_report

FIXTURE = str(pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "macd_rebound_scanner")


def test_health_check_score() -> None:
    report = run_health_check(FIXTURE)
    assert report.health_score > 0, f"Score should be > 0, got {report.health_score}"
    assert report.health_score <= 100


def test_health_check_main_py() -> None:
    report = run_health_check(FIXTURE)
    main_checks = [c for c in report.checks if c.component == "main.py"]
    assert len(main_checks) == 1
    assert main_checks[0].status == "OK"


def test_health_check_verdict() -> None:
    report = run_health_check(FIXTURE)
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in report.final_verdict


def test_render_report() -> None:
    report = run_health_check(FIXTURE)
    md = render_report(report)
    assert "# MACD Rebound Scanner Health Report" in md
    assert "health_score" in md


def main() -> None:
    test_health_check_score()
    test_health_check_main_py()
    test_health_check_verdict()
    test_render_report()
    print("test_macd_rebound_health: ALL PASS")


if __name__ == "__main__":
    main()
