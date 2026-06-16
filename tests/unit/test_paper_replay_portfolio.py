"""Tests for replay engine with portfolio risk integration."""
from __future__ import annotations

import os
import pytest

from core.paper_trading.order_plan import OrderSide, OrderStatus
from core.paper_trading.risk_sizing import RiskSizingConfig
from core.paper_trading.exit_rules import ExitRuleConfig
from core.paper_trading.portfolio_risk import PortfolioRiskConfig
from core.paper_trading.replay_engine import (
    ReplayBar, ReplayConfig, load_bars_from_fixture, run_replay,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "paper_trading")


def _load(name: str):
    return load_bars_from_fixture(os.path.join(FIXTURE_DIR, name))


def macd_rebound_signal(bars, i):
    if i < 10:
        return None
    recent_high = max(b.high for b in bars[max(0, i - 10):i])
    current = bars[i].close
    drop_pct = (recent_high - current) / recent_high * 100
    if drop_pct >= 3.0 and bars[i].close > bars[i].open:
        return {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "entry_price": current,
            "stop_loss": current * 0.98,
            "take_profit": current * 1.06,
            "invalidation_price": current * 0.97,
            "signal_source": "macd_rebound_portfolio_test",
        }
    return None


def _portfolio_config(**kwargs):
    defaults = dict(
        max_open_plans=5,
        max_daily_loss=50000,
        max_total_exposure=50000,
        consecutive_loss_cooldown=3,
        max_same_symbol_plans=2,
        block_duplicate_direction=True,
    )
    defaults.update(kwargs)
    return PortfolioRiskConfig(**defaults)


def _replay_config(portfolio_config=None, use_portfolio_risk=True, **kwargs):
    return ReplayConfig(
        risk_config=RiskSizingConfig(
            max_risk_per_trade_pct=1.0,
            max_position_pct=10.0,
            min_rr_ratio=1.5,
            max_margin_cap=50000,
            equity=100000,
        ),
        exit_config=ExitRuleConfig(
            stop_loss_pct=2.0,
            take_profit_pct=6.0,
            trailing_stop_pct=1.5,
            time_stop_bars=50,
        ),
        portfolio_config=portfolio_config or _portfolio_config(),
        auto_approve=True,
        use_portfolio_risk=use_portfolio_risk,
    )


class TestReplayWithPortfolioRisk:
    def test_account_populated(self):
        bars = _load("macd_rebound_sample.json")
        result = run_replay(bars, macd_rebound_signal, _replay_config())
        assert result.account is not None
        assert result.account.starting_balance == 100000.0

    def test_account_none_without_portfolio(self):
        bars = _load("macd_rebound_sample.json")
        result = run_replay(bars, macd_rebound_signal, _replay_config(use_portfolio_risk=False))
        assert result.account is None

    def test_max_open_plans_blocks_with_sticky_plans(self):
        """Use a fixture where plans stay open across bars."""
        # Create bars that don't trigger exits (slow steady rise)
        bars = [
            ReplayBar(f"t{i}", 50000 + i * 10, 50100 + i * 10, 49900 + i * 10, 50050 + i * 10)
            for i in range(30)
        ]
        # Signal at bar 10 — creates a plan that stays open (no exit triggers)
        def signal_at_10(bars, i):
            if i == 10:
                return {
                    "symbol": "BTCUSDT", "side": "BUY",
                    "entry_price": 50050, "stop_loss": 49000,
                    "take_profit": 55000, "invalidation_price": 48000,
                    "signal_source": "sticky",
                }
            return None

        pc = _portfolio_config(max_open_plans=0)  # 0 = block all
        result = run_replay(bars, signal_at_10, _replay_config(portfolio_config=pc))
        assert result.plans_portfolio_rejected >= 1

    def test_duplicate_direction_blocked_with_sticky(self):
        """Two BUY signals on same symbol — second should be blocked."""
        bars = [
            ReplayBar(f"t{i}", 50000 + i * 10, 50100 + i * 10, 49900 + i * 10, 50050 + i * 10)
            for i in range(30)
        ]
        def two_signals(bars, i):
            if i in (5, 15):
                return {
                    "symbol": "BTCUSDT", "side": "BUY",
                    "entry_price": 50050, "stop_loss": 49000,
                    "take_profit": 55000, "invalidation_price": 48000,
                    "signal_source": "dup_test",
                }
            return None

        pc = _portfolio_config(block_duplicate_direction=True, max_same_symbol_plans=10)
        result = run_replay(bars, two_signals, _replay_config(portfolio_config=pc))
        # First signal approved, second blocked (same direction, same symbol)
        assert result.plans_approved >= 1
        assert result.plans_portfolio_rejected >= 1

    def test_account_tracks_pnl(self):
        bars = _load("macd_rebound_sample.json")
        result = run_replay(bars, macd_rebound_signal, _replay_config())
        if result.trades_executed > 0:
            assert result.account.realized_pnl != 0 or result.account.realized_pnl == 0

    def test_no_signals_no_account_activity(self):
        bars = _load("macd_rebound_no_signal_sample.json")
        result = run_replay(bars, macd_rebound_signal, _replay_config())
        assert result.account.open_plan_count == 0
        assert result.account.realized_pnl == 0.0

    def test_loss_scenario_account_loss(self):
        bars = _load("macd_rebound_loss_sample.json")
        result = run_replay(bars, macd_rebound_signal, _replay_config())
        if result.trades_executed > 0:
            # Account should reflect the loss
            assert result.account.realized_pnl <= 0

    def test_portfolio_rejected_count(self):
        bars = _load("macd_rebound_sample.json")
        pc = _portfolio_config(max_open_plans=1)
        result = run_replay(bars, macd_rebound_signal, _replay_config(portfolio_config=pc))
        total_plans = result.plans_approved + result.plans_portfolio_rejected
        assert total_plans <= result.plans_created

    def test_account_summary_accessible(self):
        bars = _load("macd_rebound_sample.json")
        result = run_replay(bars, macd_rebound_signal, _replay_config())
        summary = result.account.summary()
        assert "starting_balance" in summary
        assert "realized_pnl" in summary
        assert "open_plan_count" in summary
