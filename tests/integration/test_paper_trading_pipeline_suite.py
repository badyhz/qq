"""Integration test: paper trading pipeline suite."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

SUITE_OUT = pathlib.Path("reports/paper_trading/suite_result.json")


def test_suite_exists() -> None:
    assert SUITE_OUT.exists()


def test_suite_passed() -> None:
    data = json.loads(SUITE_OUT.read_text(encoding="utf-8"))
    assert data["passed"] == data["total"], f"{data['passed']}/{data['total']}"


def test_suite_verdict() -> None:
    data = json.loads(SUITE_OUT.read_text(encoding="utf-8"))
    assert "PAPER_TRADING_PIPELINE_SUITE_PASS" in data["final_verdict"]
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in data["final_verdict"]


def test_suite_runners() -> None:
    data = json.loads(SUITE_OUT.read_text(encoding="utf-8"))
    assert data["total"] == 8


def main() -> None:
    test_suite_exists()
    test_suite_passed()
    test_suite_verdict()
    test_suite_runners()
    print("test_paper_trading_pipeline_suite: ALL PASS")


if __name__ == "__main__":
    main()
