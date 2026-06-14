"""Unit test: daily trade plan review."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.trade_plan_engine.daily_trade_plan_review import generate_review
from src.trade_plan_engine.models import TradePlan, PaperPosition


def _make_plan(grade="B", symbol="BTCUSDT", risk_pct=2.97) -> TradePlan:
    return TradePlan(
        plan_id="TP_test", signal_id="SIG_test", symbol=symbol,
        timeframe="5m", side="LONG", entry_type="BREAKOUT_OR_PULLBACK",
        entry_price=104500.0, entry_zone_low=104250.0, entry_zone_high=104750.0,
        stop_loss=101400.0, take_profit_1=109150.0, take_profit_2=112150.0,
        take_profit_3=116800.0, risk_pct=risk_pct, reward_risk_1=1.5,
        reward_risk_2=2.5, reward_risk_3=4.0, position_size_hint=0.016,
        max_account_risk_pct=0.01, plan_grade=grade, valid_until="4h",
        invalid_if="", explain="", dry_run_only=True)


def _make_position(status="PLANNED") -> PaperPosition:
    return PaperPosition(
        paper_position_id="PP_test", plan_id="TP_test", symbol="BTCUSDT",
        side="LONG", status=status, paper_entry_price=104500.0,
        paper_entry_time="", paper_stop_loss=101400.0,
        paper_take_profit_1=109150.0, paper_take_profit_2=112150.0,
        paper_take_profit_3=116800.0, paper_exit_price=0.0,
        paper_exit_time="", paper_exit_reason="", paper_pnl_r=0.0,
        paper_pnl_pct=0.0, bars_held=0, dry_run_only=True)


def test_review_empty() -> None:
    review = generate_review(0, [], [])
    assert review.total_signals == 0
    assert review.total_trade_plans == 0


def test_review_with_plans() -> None:
    plans = [_make_plan("A"), _make_plan("B"), _make_plan("C"), _make_plan("REJECTED")]
    review = generate_review(4, plans, [])
    assert review.total_trade_plans == 4
    assert review.grade_a_count == 1
    assert review.rejected_count == 1


def test_review_with_positions() -> None:
    positions = [_make_position("PAPER_CLOSED"), _make_position("PAPER_STOPPED")]
    review = generate_review(2, [], positions)
    assert review.paper_closed_count == 2
    assert review.tp_hit_count == 1
    assert review.stop_count == 1


def test_review_verdict() -> None:
    review = generate_review(0, [], [])
    assert "DAILY_TRADE_PLAN_REVIEW_READY" in review.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in review.final_verdict


def test_review_top_symbols() -> None:
    plans = [_make_plan(symbol="BTCUSDT"), _make_plan(symbol="BTCUSDT"), _make_plan(symbol="ETHUSDT")]
    review = generate_review(3, plans, [])
    assert review.top_symbols[0] == "BTCUSDT"


def main() -> None:
    test_review_empty()
    test_review_with_plans()
    test_review_with_positions()
    test_review_verdict()
    test_review_top_symbols()
    print("test_daily_trade_plan_review: ALL PASS")


if __name__ == "__main__":
    main()
