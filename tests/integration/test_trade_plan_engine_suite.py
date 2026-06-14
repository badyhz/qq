"""Integration test: trade plan engine suite."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

SUITE_OUT = pathlib.Path("reports/trade_plan/suite_result.json")


def test_suite_result_exists() -> None:
    assert SUITE_OUT.exists(), f"Suite result not found at {SUITE_OUT}"


def test_suite_all_passed() -> None:
    data = json.loads(SUITE_OUT.read_text(encoding="utf-8"))
    assert data["passed"] == data["total"], f"Only {data['passed']}/{data['total']} passed"


def test_suite_verdict() -> None:
    data = json.loads(SUITE_OUT.read_text(encoding="utf-8"))
    assert "TRADE_PLAN_ENGINE_SUITE_PASS" in data["final_verdict"]
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in data["final_verdict"]


def test_suite_expected_runners() -> None:
    data = json.loads(SUITE_OUT.read_text(encoding="utf-8"))
    assert data["total"] == 7


def main() -> None:
    test_suite_result_exists()
    test_suite_all_passed()
    test_suite_verdict()
    test_suite_expected_runners()
    print("test_trade_plan_engine_suite: ALL PASS")


if __name__ == "__main__":
    main()
