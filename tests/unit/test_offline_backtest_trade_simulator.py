"""Tests for offline backtest trade simulator. 25+ tests."""

import pytest

from core.offline_backtest_trade_simulator import (
    ExitReason,
    TradeOutcome,
    TradeSimulationParams,
    apply_fee,
    apply_slippage,
    compute_r_metric,
    simulate_trade,
)


def _bar(high=105.0, low=95.0, open_=100.0, close=104.0, ts=0):
    return {"timestamp": ts, "open": open_, "high": high, "low": low, "close": close, "volume": 1.0}


def _make_signal(entry_bar=5, entry_price=100.0, stop_price=98.0, tp_price=105.0):
    return {
        "signal_id": "sig_1",
        "entry_bar_index": entry_bar,
        "entry_price": entry_price,
        "stop_price": stop_price,
        "tp_price": tp_price,
    }


def _make_bars_with_tp_sl(n=30, break_high_at=None, break_low_at=None, stop_price=98.0, tp_price=105.0):
    """Create bars where TP or SL is hit at specific bar indices."""
    bars = []
    for i in range(n):
        if break_high_at is not None and i == break_high_at:
            # High above TP, low stays above stop
            bars.append(_bar(high=tp_price + 5.0, low=stop_price + 2.0, open_=100.0, close=tp_price + 2.0, ts=i))
        elif break_low_at is not None and i == break_low_at:
            # Low below stop, high stays below TP
            bars.append(_bar(high=tp_price - 5.0, low=stop_price - 2.0, open_=99.0, close=stop_price - 1.0, ts=i))
        else:
            # Normal bar: stays in range
            bars.append(_bar(high=tp_price - 3.0, low=stop_price + 1.0, open_=100.0, close=101.0, ts=i))
    return bars


class TestApplySlippage:
    def test_long_increases_price(self):
        # 5 bps = 0.05%, 100 * 1.0005 = 100.05
        result = apply_slippage(100.0, 5.0, "long")
        assert result > 100.0
        assert abs(result - 100.05) < 1e-10

    def test_short_decreases_price(self):
        # 5 bps = 0.05%, 100 * 0.9995 = 99.95
        result = apply_slippage(100.0, 5.0, "short")
        assert result < 100.0
        assert abs(result - 99.95) < 1e-10

    def test_zero_slippage(self):
        assert apply_slippage(100.0, 0.0, "long") == 100.0

    def test_zero_price_raises(self):
        with pytest.raises(ValueError, match="price"):
            apply_slippage(0.0, 5.0, "long")

    def test_negative_slippage_raises(self):
        with pytest.raises(ValueError, match="slippage_bps"):
            apply_slippage(100.0, -1.0, "long")

    def test_default_direction_is_long(self):
        result = apply_slippage(100.0, 10.0)
        assert result > 100.0


class TestApplyFee:
    def test_basic_fee(self):
        fee = apply_fee(1000.0, 10.0)
        assert abs(fee - 1.0) < 1e-10

    def test_zero_fee(self):
        assert apply_fee(1000.0, 0.0) == 0.0

    def test_zero_notional(self):
        assert apply_fee(0.0, 10.0) == 0.0

    def test_negative_notional_uses_abs(self):
        fee = apply_fee(-1000.0, 10.0)
        assert abs(fee - 1.0) < 1e-10

    def test_negative_fee_bps_raises(self):
        with pytest.raises(ValueError, match="fee_bps"):
            apply_fee(1000.0, -1.0)


class TestComputeRMetric:
    def test_positive_r(self):
        r = compute_r_metric(entry=100.0, exit_=105.0, stop_loss=98.0)
        # risk = 100 - 98 = 2, reward = 105 - 100 = 5, R = 2.5
        assert abs(r - 2.5) < 1e-6

    def test_negative_r(self):
        r = compute_r_metric(entry=100.0, exit_=99.0, stop_loss=98.0)
        # risk = 2, reward = -1, R = -0.5
        assert abs(r - (-0.5)) < 1e-6

    def test_zero_r_at_entry(self):
        r = compute_r_metric(entry=100.0, exit_=100.0, stop_loss=98.0)
        assert abs(r) < 1e-6

    def test_zero_risk_returns_zero(self):
        r = compute_r_metric(entry=100.0, exit_=105.0, stop_loss=100.0)
        assert r == 0.0

    def test_stop_at_entry_returns_zero(self):
        r = compute_r_metric(entry=100.0, exit_=105.0, stop_loss=100.0)
        assert r == 0.0


class TestExitReason:
    def test_enum_values(self):
        assert ExitReason.TAKE_PROFIT.value == "TAKE_PROFIT"
        assert ExitReason.STOP_LOSS.value == "STOP_LOSS"
        assert ExitReason.MAX_HOLD.value == "MAX_HOLD"
        assert ExitReason.END_OF_DATA.value == "END_OF_DATA"


class TestTradeOutcome:
    def test_frozen(self):
        t = TradeOutcome(
            trade_id="t1", signal_id="s1", entry_bar_index=0, exit_bar_index=5,
            entry_price=100.0, exit_price=105.0, exit_reason="TAKE_PROFIT",
            realized_r=2.5, gross_pnl=5.0, fees=0.2, slippage_cost=0.1,
            net_pnl=4.7, mfe_r=3.0, mae_r=0.5, hold_bars=5,
        )
        with pytest.raises(AttributeError):
            t.trade_id = "t2"  # type: ignore


class TestSimulateTrade:
    def test_take_profit_hit(self):
        bars = _make_bars_with_tp_sl(20, break_high_at=8)
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=98.0, tp_price=105.0)
        params = TradeSimulationParams(slippage_pct=0.0, fee_pct=0.0)
        result = simulate_trade(signal, bars, params)
        assert result.exit_reason == ExitReason.TAKE_PROFIT.value

    def test_stop_loss_hit(self):
        bars = _make_bars_with_tp_sl(20, break_low_at=8)
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=98.0, tp_price=105.0)
        params = TradeSimulationParams(slippage_pct=0.0, fee_pct=0.0)
        result = simulate_trade(signal, bars, params)
        assert result.exit_reason == ExitReason.STOP_LOSS.value

    def test_max_hold_exit(self):
        # Neither TP nor SL hit
        bars = [_bar(high=102.0, low=99.0, open_=100.0, close=101.0, ts=i) for i in range(50)]
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=90.0, tp_price=110.0)
        params = TradeSimulationParams(slippage_pct=0.0, fee_pct=0.0, max_hold_bars=10)
        result = simulate_trade(signal, bars, params)
        assert result.exit_reason in (ExitReason.MAX_HOLD.value, ExitReason.END_OF_DATA.value)

    def test_hold_bars_positive(self):
        bars = _make_bars_with_tp_sl(20, break_high_at=10)
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=98.0, tp_price=105.0)
        result = simulate_trade(signal, bars, TradeSimulationParams(slippage_pct=0.0, fee_pct=0.0))
        assert result.hold_bars >= 1

    def test_entry_price_with_slippage(self):
        bars = [_bar(high=102.0, low=99.0, open_=100.0, close=101.0, ts=i) for i in range(20)]
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=90.0, tp_price=120.0)
        params = TradeSimulationParams(slippage_pct=0.001, fee_pct=0.0, max_hold_bars=5)
        result = simulate_trade(signal, bars, params)
        # Entry price should be higher due to slippage
        assert result.entry_price >= 100.0

    def test_fees_positive(self):
        bars = [_bar(high=102.0, low=99.0, open_=100.0, close=101.0, ts=i) for i in range(20)]
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=90.0, tp_price=120.0)
        params = TradeSimulationParams(slippage_pct=0.0, fee_pct=0.001, max_hold_bars=5)
        result = simulate_trade(signal, bars, params)
        assert result.fees > 0

    def test_slippage_cost_positive(self):
        bars = [_bar(high=102.0, low=99.0, open_=100.0, close=101.0, ts=i) for i in range(20)]
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=90.0, tp_price=120.0)
        params = TradeSimulationParams(slippage_pct=0.001, fee_pct=0.0, max_hold_bars=5)
        result = simulate_trade(signal, bars, params)
        assert result.slippage_cost >= 0

    def test_mfe_non_negative(self):
        bars = _make_bars_with_tp_sl(20, break_high_at=10)
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=98.0, tp_price=105.0)
        result = simulate_trade(signal, bars, TradeSimulationParams(slippage_pct=0.0, fee_pct=0.0))
        assert result.mfe_r >= 0

    def test_mae_non_negative(self):
        bars = _make_bars_with_tp_sl(20, break_low_at=10)
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=98.0, tp_price=105.0)
        result = simulate_trade(signal, bars, TradeSimulationParams(slippage_pct=0.0, fee_pct=0.0))
        assert result.mae_r >= 0

    def test_trade_id_format(self):
        bars = [_bar(high=102.0, low=99.0, open_=100.0, close=101.0, ts=i) for i in range(20)]
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=90.0, tp_price=120.0)
        result = simulate_trade(signal, bars, TradeSimulationParams(slippage_pct=0.0, fee_pct=0.0, max_hold_bars=5))
        assert result.trade_id == "trade_sig_1"
        assert result.signal_id == "sig_1"

    def test_stop_loss_before_take_profit(self):
        """If both SL and TP could trigger on same bar, SL should take priority."""
        bars = [_bar(high=110.0, low=90.0, open_=100.0, close=100.0, ts=i) for i in range(20)]
        # TP at 105, SL at 98 — bar 8 has low=90 (hits SL) and high=110 (hits TP)
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=98.0, tp_price=105.0)
        params = TradeSimulationParams(slippage_pct=0.0, fee_pct=0.0)
        result = simulate_trade(signal, bars, params)
        # SL should trigger first since it's checked first
        assert result.exit_reason == ExitReason.STOP_LOSS.value

    def test_default_params(self):
        """Should work with None params (uses defaults)."""
        bars = [_bar(high=102.0, low=99.0, open_=100.0, close=101.0, ts=i) for i in range(20)]
        signal = _make_signal(entry_bar=5, entry_price=100.0, stop_price=90.0, tp_price=120.0)
        result = simulate_trade(signal, bars, None)
        assert isinstance(result, TradeOutcome)
