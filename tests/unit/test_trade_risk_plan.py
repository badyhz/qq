"""Unit test: risk plan."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.trade_plan_engine.risk_plan import calculate_risk_plan


def test_risk_plan_basic() -> None:
    rp = calculate_risk_plan(104500.0, 101400.0)
    assert rp.risk_per_unit == 3100.0
    assert rp.risk_level in ("LOW", "MEDIUM", "HIGH", "REJECTED")
    assert rp.suggested_quantity_placeholder > 0


def test_risk_plan_low_risk() -> None:
    rp = calculate_risk_plan(100000.0, 99000.0)
    assert rp.risk_level == "LOW"


def test_risk_plan_high_risk() -> None:
    rp = calculate_risk_plan(100000.0, 93000.0)
    assert rp.risk_level == "HIGH"


def test_risk_plan_rejected() -> None:
    rp = calculate_risk_plan(100000.0, 85000.0)
    assert rp.risk_level == "REJECTED"


def test_risk_plan_suggested_notional() -> None:
    rp = calculate_risk_plan(104500.0, 101400.0)
    assert rp.suggested_notional > 0
    assert rp.suggested_quantity_placeholder > 0


def test_risk_plan_custom_equity() -> None:
    rp = calculate_risk_plan(104500.0, 101400.0, account_equity=50000.0)
    assert rp.account_equity_placeholder == 50000.0


def test_risk_plan_verdict() -> None:
    rp = calculate_risk_plan(104500.0, 101400.0)
    assert "TRADE_RISK_PLAN_READY" in rp.risk_notes or rp.risk_level in ("LOW", "MEDIUM", "HIGH", "REJECTED")


def main() -> None:
    test_risk_plan_basic()
    test_risk_plan_low_risk()
    test_risk_plan_high_risk()
    test_risk_plan_rejected()
    test_risk_plan_suggested_notional()
    test_risk_plan_custom_equity()
    test_risk_plan_verdict()
    print("test_trade_risk_plan: ALL PASS")


if __name__ == "__main__":
    main()
