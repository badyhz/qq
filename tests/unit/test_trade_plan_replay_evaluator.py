"""Unit test: replay evaluator."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.trade_plan_engine.replay_evaluator import evaluate
from src.trade_plan_engine.models import PaperPosition


def _make_position(status="PLANNED", pnl_r=0.0) -> PaperPosition:
    return PaperPosition(
        paper_position_id="PP_test", plan_id="TP_test", symbol="BTCUSDT",
        side="LONG", status=status, paper_entry_price=104500.0,
        paper_entry_time="", paper_stop_loss=101400.0,
        paper_take_profit_1=109150.0, paper_take_profit_2=112150.0,
        paper_take_profit_3=116800.0, paper_exit_price=0.0,
        paper_exit_time="", paper_exit_reason="", paper_pnl_r=pnl_r,
        paper_pnl_pct=0.0, bars_held=0, dry_run_only=True)


def test_evaluate_empty() -> None:
    stats = evaluate([])
    assert stats.total_plans == 0
    assert stats.win_rate == 0.0


def test_evaluate_wins() -> None:
    positions = [
        _make_position("PAPER_CLOSED", 4.0),
        _make_position("PAPER_TP1_HIT", 1.5),
        _make_position("PAPER_STOPPED", -1.0),
    ]
    stats = evaluate(positions)
    assert stats.total_plans == 3
    assert stats.tp3_count == 1
    assert stats.stop_count == 1
    assert stats.win_rate > 0


def test_evaluate_all_stops() -> None:
    positions = [
        _make_position("PAPER_STOPPED", -1.0),
        _make_position("PAPER_STOPPED", -1.0),
    ]
    stats = evaluate(positions)
    assert stats.win_rate == 0.0
    assert stats.max_loss_r == -1.0


def test_evaluate_verdict() -> None:
    stats = evaluate([])
    assert "REPLAY_EVALUATOR_READY" in stats.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in stats.final_verdict


def test_evaluate_expectancy() -> None:
    positions = [
        _make_position("PAPER_CLOSED", 4.0),
        _make_position("PAPER_STOPPED", -1.0),
    ]
    stats = evaluate(positions)
    # expectancy = 0.5 * 4.0 + 0.5 * (-1.0) = 1.5
    assert abs(stats.expectancy_r - 1.5) < 0.01


def main() -> None:
    test_evaluate_empty()
    test_evaluate_wins()
    test_evaluate_all_stops()
    test_evaluate_verdict()
    test_evaluate_expectancy()
    print("test_trade_plan_replay_evaluator: ALL PASS")


if __name__ == "__main__":
    main()
