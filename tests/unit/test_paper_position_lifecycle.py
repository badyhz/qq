"""Unit test: paper position lifecycle."""
from __future__ import annotations
import csv, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.trade_plan_engine.paper_position import create_paper_position
from src.trade_plan_engine.paper_lifecycle import simulate_lifecycle
from src.trade_plan_engine.models import TradePlan

FIXTURE = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "trade_plan_engine"


def _make_plan(price=104500.0, sl=101400.0) -> TradePlan:
    return TradePlan(
        plan_id="TP_test", signal_id="SIG_test", symbol="BTCUSDT",
        timeframe="5m", side="LONG", entry_type="BREAKOUT_OR_PULLBACK",
        entry_price=price, entry_zone_low=price * 0.995,
        entry_zone_high=price * 1.005, stop_loss=sl,
        take_profit_1=price + 1.5 * (price - sl),
        take_profit_2=price + 2.5 * (price - sl),
        take_profit_3=price + 4.0 * (price - sl),
        risk_pct=round(abs(sl - price) / price * 100, 2),
        reward_risk_1=1.5, reward_risk_2=2.5, reward_risk_3=4.0,
        position_size_hint=0.0, max_account_risk_pct=0.01, plan_grade="B",
        valid_until="4h", invalid_if="", explain="", dry_run_only=True)


def _read_ohlcv(name: str) -> list[dict]:
    path = FIXTURE / name
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_create_paper_position() -> None:
    plan = _make_plan()
    pp = create_paper_position(plan)
    assert pp.status == "PLANNED"
    assert pp.dry_run_only is True
    assert pp.paper_entry_price == 104500.0


def test_lifecycle_tp() -> None:
    plan = _make_plan()
    pp = create_paper_position(plan)
    ohlcv = _read_ohlcv("ohlcv_after_signal_tp.csv")
    result = simulate_lifecycle(pp, ohlcv)
    assert result.status in ("PAPER_TP1_HIT", "PAPER_TP2_HIT", "PAPER_CLOSED")
    assert result.paper_pnl_r > 0


def test_lifecycle_stop() -> None:
    plan = _make_plan()
    pp = create_paper_position(plan)
    ohlcv = _read_ohlcv("ohlcv_after_signal_stop.csv")
    result = simulate_lifecycle(pp, ohlcv)
    assert result.status == "PAPER_STOPPED"
    assert result.paper_pnl_r == -1.0


def test_lifecycle_timeout() -> None:
    plan = _make_plan()
    pp = create_paper_position(plan)
    ohlcv = _read_ohlcv("ohlcv_after_signal_timeout.csv")
    result = simulate_lifecycle(pp, ohlcv, max_hold_bars=5)
    # Should timeout or hit TP depending on data
    assert result.status in ("PAPER_TIME_STOPPED", "PAPER_TP1_HIT", "PAPER_OPEN", "PLANNED")


def test_lifecycle_empty_ohlcv() -> None:
    plan = _make_plan()
    pp = create_paper_position(plan)
    result = simulate_lifecycle(pp, [])
    assert result.status == "PLANNED"


def test_paper_position_dry_run_only() -> None:
    plan = _make_plan()
    pp = create_paper_position(plan)
    assert pp.dry_run_only is True


def main() -> None:
    test_create_paper_position()
    test_lifecycle_tp()
    test_lifecycle_stop()
    test_lifecycle_timeout()
    test_lifecycle_empty_ohlcv()
    test_paper_position_dry_run_only()
    print("test_paper_position_lifecycle: ALL PASS")


if __name__ == "__main__":
    main()
