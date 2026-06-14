"""Unit test: paper trading pipeline safety regression."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_pipeline.pipeline_safety_regression import run_safety_regression


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


def main() -> None:
    test_safety_clean()
    test_safety_checked()
    test_safety_verdict()
    print("test_paper_trading_pipeline_safety: ALL PASS")


if __name__ == "__main__":
    main()
