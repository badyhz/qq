"""Edge case tests for paper trading system."""
from __future__ import annotations

import pytest
from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus, ExitReason
from core.paper_trading.risk_sizing import RiskSizingConfig, calculate_risk, apply_risk_sizing
from core.paper_trading.exit_rules import ExitRuleConfig, evaluate_exits, ExitSignal
from core.paper_trading.signal_to_plan_adapter import signal_envelope_to_order_plan
from core.paper_trading.human_approval_gate import HumanApprovalGate
from core.paper_trading.paper_ledger import PaperLedger, LedgerEntry
from core.paper_trading.account_state import AccountState
from core.paper_trading.portfolio_risk import PortfolioRiskConfig, check_portfolio_risk
from core.paper_trading.lifecycle import (
    LifecycleError, transition_to_approval, transition_to_cancelled,
    transition_to_closed, is_paper_safe,
)


def _plan(**kwargs):
    defaults = dict(
        plan_id="E-001", symbol="BTCUSDT", side=OrderSide.BUY,
        entry_price=50000, stop_loss=49000, take_profit=53000,
        invalidation_price=48500, risk_amount=100, position_size=0.1,
        status=OrderStatus.PLANNED_ONLY,
    )
    defaults.update(kwargs)
    return OrderPlan(**defaults)


class TestInvalidPrices:
    """Edge cases with invalid or boundary prices."""

    def test_zero_entry(self):
        result = calculate_risk(0, 49000, 53000, RiskSizingConfig())
        assert not result.approved
        assert "positive" in result.rejection_reason.lower()

    def test_negative_stop_loss(self):
        result = calculate_risk(50000, -100, 53000, RiskSizingConfig())
        assert not result.approved

    def test_zero_take_profit(self):
        result = calculate_risk(50000, 49000, 0, RiskSizingConfig())
        assert not result.approved

    def test_sl_equals_entry(self):
        result = calculate_risk(50000, 50000, 53000, RiskSizingConfig())
        assert not result.approved
        assert "stop loss equals entry" in result.rejection_reason.lower()

    def test_very_small_risk(self):
        result = calculate_risk(50000, 49999.99, 53000, RiskSizingConfig())
        assert result.approved
        assert result.rr_ratio > 1.5


class TestShortSideEdgeCases:
    """Edge cases for SELL side."""

    def test_short_signal_adapter(self):
        envelope = {
            "symbol": "BTCUSDT", "side": "SELL",
            "entry_price": 50000, "stop_loss": 51000,
            "take_profit": 47000, "invalidation_price": 51500,
            "signal_source": "test",
        }
        plan = signal_envelope_to_order_plan(envelope)
        assert plan is not None
        assert plan.side == OrderSide.SELL

    def test_short_risk_sizing(self):
        result = calculate_risk(50000, 51000, 47000, RiskSizingConfig(), OrderSide.SELL)
        assert result.approved
        assert result.rr_ratio == pytest.approx(3.0)

    def test_short_exit_stop_loss(self):
        plan = _plan(side=OrderSide.SELL, entry_price=50000, stop_loss=51000,
                     take_profit=47000, invalidation_price=52000)
        config = ExitRuleConfig()
        # Price rises above stop loss but below invalidation
        signal = evaluate_exits(plan, 51500, 49000, 5, config)
        assert signal is not None
        assert signal.reason == ExitReason.STOP_LOSS

    def test_short_exit_take_profit(self):
        plan = _plan(side=OrderSide.SELL, entry_price=50000, stop_loss=51000, take_profit=47000)
        config = ExitRuleConfig()
        # Price drops to take profit
        signal = evaluate_exits(plan, 46000, 50000, 5, config)
        assert signal is not None
        assert signal.reason == ExitReason.TAKE_PROFIT

    def test_short_invalidation(self):
        plan = _plan(side=OrderSide.SELL, entry_price=50000, stop_loss=51000,
                     take_profit=47000, invalidation_price=51500)
        config = ExitRuleConfig()
        signal = evaluate_exits(plan, 52000, 49000, 5, config)
        assert signal is not None
        assert signal.reason == ExitReason.SIGNAL_INVALIDATED


class TestDuplicateSignals:
    """Edge cases with duplicate or rapid signals."""

    def test_same_bar_two_signals(self):
        """Replay engine only processes one signal per bar."""
        from core.paper_trading.replay_engine import ReplayBar, ReplayConfig, run_replay
        bars = [ReplayBar(f"t{i}", 50000, 50500, 49800, 50200) for i in range(20)]
        call_count = 0
        def double_signal(bars, i):
            nonlocal call_count
            call_count += 1
            if i == 5:
                return {"symbol": "BTCUSDT", "side": "BUY",
                        "entry_price": 50200, "stop_loss": 49200,
                        "take_profit": 53200, "invalidation_price": 48700,
                        "signal_source": "double"}
            return None
        config = ReplayConfig(auto_approve=True)
        result = run_replay(bars, double_signal, config)
        assert result.signals_generated == 1


class TestLedgerEdgeCases:
    """Edge cases for paper ledger."""

    def test_all_breakeven(self):
        ledger = PaperLedger()
        for i in range(5):
            plan = _plan(plan_id=f"B-{i}")
            ledger.record(LedgerEntry(
                plan=plan, entry_bar=0, exit_bar=1,
                exit_price=50000, exit_reason=ExitReason.TIME_STOP,
                pnl=0, rr_actual=0,
            ))
        assert ledger.win_rate == 0.0
        assert ledger.total_pnl == 0.0
        assert ledger.breakeven == 5

    def test_single_trade_stats(self):
        ledger = PaperLedger()
        plan = _plan()
        ledger.record(LedgerEntry(
            plan=plan, entry_bar=0, exit_bar=1,
            exit_price=51000, exit_reason=ExitReason.TAKE_PROFIT,
            pnl=100, rr_actual=1.0,
        ))
        assert ledger.win_rate == 1.0
        assert ledger.consecutive_losses == 0
        assert ledger.max_drawdown == 0


class TestGateEdgeCases:
    """Edge cases for human approval gate."""

    def test_gate_cancel_from_waiting(self):
        gate = HumanApprovalGate()
        plan = _plan(status=OrderStatus.WAITING_FOR_HUMAN_APPROVAL)
        result = gate.cancel(plan)
        assert result.status == OrderStatus.CANCELLED

    def test_gate_approve_from_waiting(self):
        gate = HumanApprovalGate()
        plan = _plan(status=OrderStatus.WAITING_FOR_HUMAN_APPROVAL)
        result = gate.approve(plan)
        # In paper mode, approve keeps in WAITING
        assert result.status == OrderStatus.WAITING_FOR_HUMAN_APPROVAL

    def test_gate_pending_filter(self):
        gate = HumanApprovalGate()
        plans = [
            _plan(plan_id="G-1", status=OrderStatus.WAITING_FOR_HUMAN_APPROVAL),
            _plan(plan_id="G-2", status=OrderStatus.CANCELLED),
            _plan(plan_id="G-3", status=OrderStatus.WAITING_FOR_HUMAN_APPROVAL),
        ]
        pending = gate.get_pending_plans(plans)
        assert len(pending) == 2


class TestLifecycleEdgeCases:
    """Edge cases for lifecycle state machine."""

    def test_double_close(self):
        plan = _plan(status=OrderStatus.SIMULATED_CLOSED)
        with pytest.raises(LifecycleError):
            transition_to_closed(plan, ExitReason.TAKE_PROFIT, 100)

    def test_cancel_from_closed(self):
        plan = _plan(status=OrderStatus.SIMULATED_CLOSED)
        with pytest.raises(LifecycleError):
            transition_to_cancelled(plan)

    def test_all_statuses_paper_safe(self):
        for s in OrderStatus:
            assert is_paper_safe(s.value)


class TestAccountCooldownEdgeCases:
    """Edge cases for account cooldown."""

    def test_cooldown_blocks_open(self):
        acct = AccountState(consecutive_loss_cooldown=2)
        for i in range(2):
            p = _plan(plan_id=f"C-{i}")
            acct.reserve_margin(p)
            acct.close_plan(p, pnl=-100)
        assert acct.is_cooling_down
        allowed, reason = acct.can_open_new_plan()
        assert not allowed
        assert "Cooldown" in reason

    def test_cooldown_resets_after_win(self):
        acct = AccountState(consecutive_loss_cooldown=3)
        # 2 losses
        for i in range(2):
            p = _plan(plan_id=f"C-{i}")
            acct.reserve_margin(p)
            acct.close_plan(p, pnl=-100)
        assert not acct.is_cooling_down
        # Win
        p = _plan(plan_id="C-win")
        acct.reserve_margin(p)
        acct.close_plan(p, pnl=200)
        assert acct.consecutive_losses == 0
        assert not acct.is_cooling_down
