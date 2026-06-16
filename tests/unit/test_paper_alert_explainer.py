"""Tests for paper alert explainer."""
from __future__ import annotations
import pytest
from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus
from core.paper_trading.alert_explainer import explain_alert, format_alert_text


def _buy_plan(status=OrderStatus.WAITING_FOR_HUMAN_APPROVAL):
    return OrderPlan(
        plan_id="A-001", symbol="BTCUSDT", side=OrderSide.BUY,
        entry_price=50000, stop_loss=49000, take_profit=53000,
        invalidation_price=49500, risk_amount=100, position_size=0.1,
        status=status, signal_source="macd_rebound",
    )


def _sell_plan():
    return OrderPlan(
        plan_id="A-002", symbol="ETHUSDT", side=OrderSide.SELL,
        entry_price=3000, stop_loss=3100, take_profit=2700,
        invalidation_price=3050, risk_amount=50, position_size=0.5,
        status=OrderStatus.WAITING_FOR_HUMAN_APPROVAL,
    )


class TestExplainAlert:
    def test_buy_alert(self):
        alert = explain_alert(_buy_plan())
        assert alert["symbol"] == "BTCUSDT"
        assert alert["direction"] == "LONG"
        assert alert["entry_price"] == 50000
        assert alert["rr_ratio"] == 3.0

    def test_sell_alert(self):
        alert = explain_alert(_sell_plan())
        assert alert["direction"] == "SHORT"
        assert alert["symbol"] == "ETHUSDT"

    def test_trigger_reason(self):
        alert = explain_alert(_buy_plan())
        assert "macd_rebound" in alert["trigger_reason"]

    def test_no_signal_source(self):
        plan = OrderPlan(
            plan_id="A-003", symbol="BTCUSDT", side=OrderSide.BUY,
            entry_price=50000, stop_loss=49000, take_profit=53000,
            invalidation_price=49500, risk_amount=100, position_size=0.1,
        )
        alert = explain_alert(plan)
        assert "Manual" in alert["trigger_reason"]

    def test_status_waiting(self):
        alert = explain_alert(_buy_plan())
        assert "WAITING_FOR_HUMAN_APPROVAL" in alert["status"]

    def test_status_cancelled(self):
        alert = explain_alert(_buy_plan(OrderStatus.CANCELLED))
        assert "CANCELLED" in alert["status"]

    def test_risk_warning_present(self):
        alert = explain_alert(_buy_plan())
        assert "PAPER TRADE" in alert["risk_warning"]
        assert "No real order" in alert["risk_warning"]

    def test_risk_amount_in_alert(self):
        alert = explain_alert(_buy_plan())
        assert alert["risk_amount"] == 100

    def test_all_fields_present(self):
        alert = explain_alert(_buy_plan())
        required = [
            "trigger_reason", "symbol", "direction", "entry_zone",
            "entry_price", "stop_loss", "take_profit", "invalidation_price",
            "risk_amount", "position_size", "rr_ratio", "status", "risk_warning",
        ]
        for key in required:
            assert key in alert, f"Missing key: {key}"


class TestFormatAlertText:
    def test_format_contains_symbol(self):
        text = format_alert_text(explain_alert(_buy_plan()))
        assert "BTCUSDT" in text

    def test_format_contains_direction(self):
        text = format_alert_text(explain_alert(_buy_plan()))
        assert "LONG" in text

    def test_format_contains_prices(self):
        text = format_alert_text(explain_alert(_buy_plan()))
        assert "50000" in text
        assert "49000" in text
        assert "53000" in text

    def test_format_contains_status(self):
        text = format_alert_text(explain_alert(_buy_plan()))
        assert "WAITING_FOR_HUMAN_APPROVAL" in text

    def test_format_contains_risk_warning(self):
        text = format_alert_text(explain_alert(_buy_plan()))
        assert "PAPER TRADE" in text
