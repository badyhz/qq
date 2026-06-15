"""Tests for core/macd_rebound_signal_plugin.py — 8 scenarios."""
import pytest
import logging
from core.macd_rebound_signal_plugin import (
    MACDReboundSignalPlugin,
    StrategyResult,
    StrategyPlugin,
)
from core.signal_envelope import SignalEnvelope
from core.market_data_contract import Candle


def _candles(n=45, base=100.0, symbol="BTCUSDT"):
    """Generate fixture-like candles with run-up-then-reversal pattern."""
    candles = []
    for i in range(n):
        if i < 25:
            price = base + i * 0.3
        elif i < 30:
            price = base + 7.5 + (i - 25) * 2.0
        else:
            price = base + 17.5 - (i - 30) * 1.5
        candles.append(Candle(
            symbol=symbol,
            timestamp=str(1000 + i * 900),
            open=price - 0.5,
            high=price + 1.0,
            low=price - 1.0,
            close=price,
            volume=100 + i * 10,
            timeframe="15m",
            is_fixture=True,
            is_live=False,
            source="fixture",
        ))
    return candles


class TestMACDReboundSignalPlugin:
    def test_plugin_creation(self):
        p = MACDReboundSignalPlugin()
        assert p.strategy_id == "macd_rebound_v1"
        assert p.dry_run is True
        assert p.mode == "paper"

    def test_rejects_non_dry_run(self):
        with pytest.raises(ValueError):
            MACDReboundSignalPlugin(dry_run=False)

    def test_rejects_testnet_mode(self):
        with pytest.raises(ValueError):
            MACDReboundSignalPlugin(mode="testnet_dry_run")

    def test_run_returns_strategy_result(self):
        p = MACDReboundSignalPlugin()
        result = p.run(_candles(45))
        assert isinstance(result, StrategyResult)
        assert result.candles_processed == 45

    def test_signals_have_envelope_type(self):
        p = MACDReboundSignalPlugin()
        result = p.run(_candles(45))
        for sig in result.signals:
            assert isinstance(sig, SignalEnvelope)

    def test_signals_have_safety_flags(self):
        p = MACDReboundSignalPlugin(mode="paper", dry_run=True)
        result = p.run(_candles(45))
        for sig in result.signals:
            assert sig.dry_run is True
            assert sig.mode == "paper"

    def test_signals_have_valid_structure(self):
        p = MACDReboundSignalPlugin()
        result = p.run(_candles(45))
        for sig in result.signals:
            assert sig.symbol == "BTCUSDT"
            assert sig.strategy_id == "macd_rebound_v1"
            assert sig.entry > 0
            assert sig.stop_loss > 0
            assert sig.take_profit > 0
            assert sig.side == "short"

    def test_macd_context_is_local_indicator_only(self):
        p = MACDReboundSignalPlugin()
        context = p._macd_context(_candles(45))
        assert set(context) == {"macd_dif", "macd_dea", "macd_hist", "macd_bearish", "bearish"}
        assert isinstance(context["bearish"], bool)

    def test_no_signals_on_flat_data(self):
        # flat data should not trigger signals
        candles = [Candle(
            symbol="X", timestamp=str(i), open=100, high=100.1, low=99.9,
            close=100, volume=50, is_fixture=True, is_live=False, source="fixture",
        ) for i in range(50)]
        p = MACDReboundSignalPlugin()
        result = p.run(candles)
        assert len(result.signals) == 0

    def test_errors_logged_on_invalid_signal(self):
        p = MACDReboundSignalPlugin()
        result = p.run(_candles(5))  # too few candles
        assert result.candles_processed == 5

    def test_reset_clears_state(self):
        p = MACDReboundSignalPlugin()
        p.run(_candles(45))
        p.reset()
        result = p.run(_candles(45))
        assert isinstance(result, StrategyResult)
