"""Tests for signal to plan adapter."""
from __future__ import annotations
import pytest
from core.paper_trading.signal_to_plan_adapter import signal_envelope_to_order_plan
from core.paper_trading.order_plan import OrderSide, OrderStatus


def _valid_buy_envelope():
    return {
        "symbol": "BTCUSDT", "side": "BUY",
        "entry_price": 50000, "stop_loss": 49000, "take_profit": 53000,
        "signal_source": "macd_rebound",
    }


def _valid_sell_envelope():
    return {
        "symbol": "ETHUSDT", "side": "SELL",
        "entry_price": 3000, "stop_loss": 3100, "take_profit": 2700,
    }


class TestSignalToPlanAdapter:
    def test_valid_buy(self):
        plan = signal_envelope_to_order_plan(_valid_buy_envelope())
        assert plan is not None
        assert plan.side == OrderSide.BUY
        assert plan.status == OrderStatus.PLANNED_ONLY
        assert plan.symbol == "BTCUSDT"
        assert plan.signal_source == "macd_rebound"

    def test_valid_sell(self):
        plan = signal_envelope_to_order_plan(_valid_sell_envelope())
        assert plan is not None
        assert plan.side == OrderSide.SELL

    def test_with_invalidation(self):
        env = _valid_buy_envelope()
        env["invalidation_price"] = 49500
        plan = signal_envelope_to_order_plan(env)
        assert plan.invalidation_price == 49500

    def test_default_invalidation_is_sl(self):
        plan = signal_envelope_to_order_plan(_valid_buy_envelope())
        assert plan.invalidation_price == 49000

    def test_missing_symbol(self):
        env = _valid_buy_envelope()
        del env["symbol"]
        assert signal_envelope_to_order_plan(env) is None

    def test_missing_side(self):
        env = _valid_buy_envelope()
        del env["side"]
        assert signal_envelope_to_order_plan(env) is None

    def test_missing_entry(self):
        env = _valid_buy_envelope()
        del env["entry_price"]
        assert signal_envelope_to_order_plan(env) is None

    def test_invalid_side(self):
        env = _valid_buy_envelope()
        env["side"] = "HOLD"
        assert signal_envelope_to_order_plan(env) is None

    def test_buy_sl_above_entry(self):
        env = _valid_buy_envelope()
        env["stop_loss"] = 51000
        assert signal_envelope_to_order_plan(env) is None

    def test_sell_sl_below_entry(self):
        env = _valid_sell_envelope()
        env["stop_loss"] = 2900
        assert signal_envelope_to_order_plan(env) is None

    def test_buy_tp_below_entry(self):
        env = _valid_buy_envelope()
        env["take_profit"] = 49000
        assert signal_envelope_to_order_plan(env) is None

    def test_sell_tp_above_entry(self):
        env = _valid_sell_envelope()
        env["take_profit"] = 3200
        assert signal_envelope_to_order_plan(env) is None

    def test_negative_entry(self):
        env = _valid_buy_envelope()
        env["entry_price"] = -1
        assert signal_envelope_to_order_plan(env) is None

    def test_plan_id_prefix(self):
        plan = signal_envelope_to_order_plan(_valid_buy_envelope(), "MACD", 42)
        assert plan.plan_id == "MACD-0042"

    def test_risk_size_zero_initially(self):
        plan = signal_envelope_to_order_plan(_valid_buy_envelope())
        assert plan.risk_amount == 0.0
        assert plan.position_size == 0.0
