"""Unit test: trade plan engine safety regression."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.trade_plan_engine.trade_plan_safety_regression import run_safety_regression, render_report


def test_safety_clean() -> None:
    report = run_safety_regression()
    assert report.total_flagged == 0, f"Flagged: {[c.detail for c in report.checks if c.status == 'FLAGGED']}"


def test_safety_checked() -> None:
    report = run_safety_regression()
    assert report.total_checked > 0


def test_safety_verdict() -> None:
    report = run_safety_regression()
    assert "NO_SUBMIT_SAFETY_PASS" in report.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in report.final_verdict
    assert "REAL_TRADING_NOT_ALLOWED" in report.final_verdict


def test_render_report() -> None:
    report = run_safety_regression()
    md = render_report(report)
    assert "# Trade Plan Engine Safety Regression" in md


def main() -> None:
    test_safety_clean()
    test_safety_checked()
    test_safety_verdict()
    test_render_report()
    print("test_trade_plan_engine_safety: ALL PASS")


if __name__ == "__main__":
    main()
