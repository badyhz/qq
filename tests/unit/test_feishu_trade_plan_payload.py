"""Unit test: Feishu trade plan payload."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.trade_plan_engine.feishu_trade_plan_payload import generate_payload
from src.trade_plan_engine.models import TradePlan


def _make_plan() -> TradePlan:
    return TradePlan(
        plan_id="TP_test", signal_id="SIG_test", symbol="BTCUSDT",
        timeframe="5m", side="LONG", entry_type="BREAKOUT_OR_PULLBACK",
        entry_price=104500.0, entry_zone_low=104250.0, entry_zone_high=104750.0,
        stop_loss=101400.0, take_profit_1=109150.0, take_profit_2=112150.0,
        take_profit_3=116800.0, risk_pct=2.97, reward_risk_1=1.5,
        reward_risk_2=2.5, reward_risk_3=4.0, position_size_hint=0.016,
        max_account_risk_pct=0.01, plan_grade="B", valid_until="4h",
        invalid_if="price < ma25", explain="test", dry_run_only=True)


def test_payload_dry_run_only() -> None:
    plan = _make_plan()
    payload = generate_payload(plan)
    assert payload.dry_run_only is True


def test_payload_fields() -> None:
    plan = _make_plan()
    payload = generate_payload(plan)
    assert payload.symbol == "BTCUSDT"
    assert payload.stop_loss == 101400.0
    assert payload.take_profit_1 > payload.stop_loss


def test_payload_risk_warning() -> None:
    plan = _make_plan()
    payload = generate_payload(plan)
    assert "DRY-RUN" in payload.risk_warning


def test_payload_verdict() -> None:
    plan = _make_plan()
    payload = generate_payload(plan)
    assert "DRY_RUN_READY" in payload.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in payload.final_verdict


def test_payload_title() -> None:
    plan = _make_plan()
    payload = generate_payload(plan)
    assert "DRY-RUN" in payload.title
    assert "BTCUSDT" in payload.title


def main() -> None:
    test_payload_dry_run_only()
    test_payload_fields()
    test_payload_risk_warning()
    test_payload_verdict()
    test_payload_title()
    print("test_feishu_trade_plan_payload: ALL PASS")


if __name__ == "__main__":
    main()
