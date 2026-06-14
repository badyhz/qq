"""Unit test: paper ops canary runner."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_deployment.canary_runner import run_canary


def test_canary_passes() -> None:
    report = run_canary()
    assert report.canary_status == "PASS", f"Failed: {report.failed_steps}"


def test_canary_all_steps() -> None:
    report = run_canary()
    assert report.steps_total >= 9


def test_canary_verdict_format() -> None:
    report = run_canary()
    assert "PAPER_OPS_CANARY_DRY_RUN_READY" in report.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in report.final_verdict


def test_canary_to_dict() -> None:
    report = run_canary()
    d = report.to_dict()
    assert "canary_id" in d
    assert "failed_steps" in d


def main() -> None:
    test_canary_passes()
    test_canary_all_steps()
    test_canary_verdict_format()
    test_canary_to_dict()
    print("test_paper_ops_canary_runner: ALL PASS")


if __name__ == "__main__":
    main()
