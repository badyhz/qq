"""Tests for paper exit rules."""
from __future__ import annotations
import pytest
from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus, ExitReason
from core.paper_trading.exit_rules import (
    ExitRuleConfig, ExitSignal,
    check_stop_loss, check_take_profit, check_trailing_stop,
    check_time_stop, check_invalidation, evaluate_exits,
)


def _buy_plan(sl=49000, tp=53000, inv=49500, size=0.1):
    return OrderPlan(
        plan_id="E-001", symbol="BTCUSDT", side=OrderSide.BUY,
        entry_price=50000, stop_loss=sl, take_profit=tp,
        invalidation_price=inv, risk_amount=100, position_size=size,
    )


def _sell_plan(sl=3100, tp=2700, inv=3050, size=0.5):
    return OrderPlan(
        plan_id="E-002", symbol="ETHUSDT", side=OrderSide.SELL,
        entry_price=3000, stop_loss=sl, take_profit=tp,
        invalidation_price=inv, risk_amount=50, position_size=size,
    )


class TestStopLoss:
    def test_buy_sl_hit(self):
        result = check_stop_loss(_buy_plan(), 48900)
        assert result is not None
        assert result.reason == ExitReason.STOP_LOSS
        assert result.pnl < 0

    def test_buy_sl_not_hit(self):
        assert check_stop_loss(_buy_plan(), 50000) is None

    def test_sell_sl_hit(self):
        result = check_stop_loss(_sell_plan(), 3150)
        assert result is not None
        assert result.reason == ExitReason.STOP_LOSS

    def test_sell_sl_not_hit(self):
        assert check_stop_loss(_sell_plan(), 3050) is None


class TestTakeProfit:
    def test_buy_tp_hit(self):
        result = check_take_profit(_buy_plan(), 53500)
        assert result is not None
        assert result.reason == ExitReason.TAKE_PROFIT
        assert result.pnl > 0

    def test_buy_tp_not_hit(self):
        assert check_take_profit(_buy_plan(), 52000) is None

    def test_sell_tp_hit(self):
        result = check_take_profit(_sell_plan(), 2600)
        assert result is not None
        assert result.reason == ExitReason.TAKE_PROFIT

    def test_sell_tp_not_hit(self):
        assert check_take_profit(_sell_plan(), 2800) is None


class TestTrailingStop:
    def test_buy_trailing_hit(self):
        # trail_price = 53000 * (1 - 0.02) = 51940. Current 51000 < 51940, hit
        result = check_trailing_stop(_buy_plan(), 51000, 53000, 2.0)
        assert result is not None
        assert result.reason == ExitReason.TRAILING_STOP

    def test_buy_trailing_not_hit(self):
        assert check_trailing_stop(_buy_plan(), 51800, 52000, 2.0) is None

    def test_sell_trailing_hit(self):
        result = check_trailing_stop(_sell_plan(), 2950, 2800, 2.0)
        assert result is not None
        assert result.reason == ExitReason.TRAILING_STOP

    def test_sell_trailing_not_hit(self):
        assert check_trailing_stop(_sell_plan(), 2850, 2800, 2.0) is None


class TestTimeStop:
    def test_time_stop_hit(self):
        result = check_time_stop(_buy_plan(), 50, 50000, 50)
        assert result is not None
        assert result.reason == ExitReason.TIME_STOP

    def test_time_stop_not_hit(self):
        assert check_time_stop(_buy_plan(), 49, 50000, 50) is None


class TestInvalidation:
    def test_buy_invalidation_hit(self):
        result = check_invalidation(_buy_plan(), 49400)
        assert result is not None
        assert result.reason == ExitReason.SIGNAL_INVALIDATED

    def test_buy_invalidation_not_hit(self):
        assert check_invalidation(_buy_plan(), 49600) is None

    def test_sell_invalidation_hit(self):
        result = check_invalidation(_sell_plan(), 3060)
        assert result is not None
        assert result.reason == ExitReason.SIGNAL_INVALIDATED


class TestEvaluateExits:
    def test_no_exit(self):
        result = evaluate_exits(_buy_plan(), 50500, 50500, 10, ExitRuleConfig())
        assert result is None

    def test_priority_invalidation_over_sl(self):
        # inv=49500, sl=49000 — price 49400 hits invalidation first
        result = evaluate_exits(_buy_plan(inv=49500, sl=49000), 49400, 50000, 10, ExitRuleConfig())
        assert result.reason == ExitReason.SIGNAL_INVALIDATED

    def test_priority_sl_over_trailing(self):
        # inv=49500, sl=49000 — price 48900 hits invalidation first (higher priority)
        result = evaluate_exits(_buy_plan(sl=49000, inv=48800), 48900, 52000, 10, ExitRuleConfig())
        assert result.reason == ExitReason.STOP_LOSS

    def test_closed_plan_no_exit(self):
        plan = _buy_plan().with_status(OrderStatus.SIMULATED_CLOSED)
        assert evaluate_exits(plan, 48000, 52000, 100, ExitRuleConfig()) is None

    def test_cancelled_plan_no_exit(self):
        plan = _buy_plan().with_status(OrderStatus.CANCELLED)
        assert evaluate_exits(plan, 48000, 52000, 100, ExitRuleConfig()) is None
