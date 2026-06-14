"""Unit test: trade plan models."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.trade_plan_engine.models import (
    SignalCandidate, TradePlan, RiskPlan, ExitPlan, PaperPosition, new_id, utc_now_iso)


def test_signal_candidate_creation() -> None:
    sc = SignalCandidate(
        signal_id="SIG_test", symbol="BTCUSDT", timeframe="5m",
        signal_time="2026-06-12T16:45:00", price=104500.0, signal_level="B",
        drop_pct=3.5, macd_dif=1.2e-05, macd_dea=1.1e-05, macd_hist=1.0e-06,
        ma7=104200.0, ma25=103800.0, ma99=103000.0, volume=5200.0,
        volume_ma5=3500.0, volume_ratio=1.49, above_ma99=True,
        reason="test signal", source="macd_rebound_scanner")
    d = sc.to_dict()
    assert d["symbol"] == "BTCUSDT"
    assert d["price"] == 104500.0
    assert d["source"] == "macd_rebound_scanner"


def test_trade_plan_dry_run_only() -> None:
    tp = TradePlan(
        plan_id="TP_test", signal_id="SIG_test", symbol="BTCUSDT",
        timeframe="5m", side="LONG", entry_type="BREAKOUT_OR_PULLBACK",
        entry_price=104500.0, entry_zone_low=104250.0, entry_zone_high=104750.0,
        stop_loss=101400.0, take_profit_1=109150.0, take_profit_2=112150.0,
        take_profit_3=116800.0, risk_pct=2.97, reward_risk_1=1.5,
        reward_risk_2=2.5, reward_risk_3=4.0, position_size_hint=0.016,
        max_account_risk_pct=0.01, plan_grade="B", valid_until="4h",
        invalid_if="price < ma25", explain="test", dry_run_only=True)
    assert tp.dry_run_only is True
    assert tp.side == "LONG"


def test_risk_plan_creation() -> None:
    rp = RiskPlan(
        risk_plan_id="RP_test", account_equity_placeholder=10000.0,
        max_account_risk_pct=0.01, risk_per_trade_pct=0.005,
        entry_price=104500.0, stop_loss=101400.0, risk_per_unit=3100.0,
        suggested_notional=168.55, suggested_quantity_placeholder=0.001613,
        leverage_hint=2, risk_level="MEDIUM", risk_notes="test")
    d = rp.to_dict()
    assert d["risk_level"] == "MEDIUM"
    assert d["entry_price"] == 104500.0


def test_exit_plan_creation() -> None:
    ep = ExitPlan(
        exit_plan_id="EP_test", stop_loss_rule="stop at 101400",
        tp1_rule="tp1 at 109150", tp2_rule="tp2 at 112150",
        tp3_rule="tp3 at 116800", time_stop_rule="exit after 48 bars",
        signal_failure_rule="exit if below ma25",
        trailing_stop_rule="move to breakeven after tp1",
        manual_review_required=False)
    assert ep.manual_review_required is False


def test_paper_position_creation() -> None:
    pp = PaperPosition(
        paper_position_id="PP_test", plan_id="TP_test", symbol="BTCUSDT",
        side="LONG", status="PLANNED", paper_entry_price=104500.0,
        paper_entry_time="", paper_stop_loss=101400.0,
        paper_take_profit_1=109150.0, paper_take_profit_2=112150.0,
        paper_take_profit_3=116800.0, paper_exit_price=0.0,
        paper_exit_time="", paper_exit_reason="", paper_pnl_r=0.0,
        paper_pnl_pct=0.0, bars_held=0, dry_run_only=True)
    assert pp.status == "PLANNED"
    assert pp.dry_run_only is True


def test_new_id_prefix() -> None:
    tid = new_id("TEST")
    assert tid.startswith("TEST_")
    assert len(tid) == 17  # TEST_ + 12 hex chars


def test_utc_now_iso() -> None:
    ts = utc_now_iso()
    assert "T" in ts
    assert "+" in ts or "Z" in ts


def main() -> None:
    test_signal_candidate_creation()
    test_trade_plan_dry_run_only()
    test_risk_plan_creation()
    test_exit_plan_creation()
    test_paper_position_creation()
    test_new_id_prefix()
    test_utc_now_iso()
    print("test_trade_plan_models: ALL PASS")


if __name__ == "__main__":
    main()
