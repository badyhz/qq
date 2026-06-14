"""Integration test: MACD rebound safety regression."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.external_scanner_integrations.macd_rebound_safety_regression import run_safety_regression, render_report


def test_safety_clean() -> None:
    report = run_safety_regression()
    assert report.total_flagged == 0, f"Flagged: {[c.detail for c in report.checks if c.status == 'FLAGGED']}"


def test_safety_checked() -> None:
    report = run_safety_regression()
    assert report.total_checked > 0


def test_safety_verdict() -> None:
    report = run_safety_regression()
    assert "SAFETY_REGRESSION_PASS" in report.final_verdict


def test_render_report() -> None:
    report = run_safety_regression()
    md = render_report(report)
    assert "# MACD Rebound Safety Regression" in md


def main() -> None:
    test_safety_clean()
    test_safety_checked()
    test_safety_verdict()
    test_render_report()
    print("test_macd_rebound_integration_safety: ALL PASS")


if __name__ == "__main__":
    main()
