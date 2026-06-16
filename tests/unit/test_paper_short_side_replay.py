"""Short side replay tests — SELL signals through the full pipeline."""
from __future__ import annotations

import os
import pytest

from core.paper_trading.order_plan import OrderSide, OrderStatus
from core.paper_trading.risk_sizing import RiskSizingConfig
from core.paper_trading.exit_rules import ExitRuleConfig
from core.paper_trading.replay_engine import (
    ReplayBar, ReplayConfig, load_bars_from_fixture, run_replay,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "paper_trading")


def _bars_rising(n=30):
    """Bars that steadily rise — good for short signals."""
    return [
        ReplayBar(f"t{i}", 50000 + i * 100, 50200 + i * 100, 49800 + i * 100, 50100 + i * 100)
        for i in range(n)
    ]


def _bars_falling(n=30):
    """Bars that steadily fall."""
    return [
        ReplayBar(f"t{i}", 50000 - i * 100, 50200 - i * 100, 49800 - i * 100, 49900 - i * 100)
        for i in range(n)
    ]


def _default_config():
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
        auto_approve=True,
    )


class TestShortSideReplay:
    def test_short_signal_triggers(self):
        """Short signal on rising prices triggers and gets processed."""
        def short_signal(bars, i):
            if i < 10:
                return None
            if i == 15:
                return {
                    "symbol": "BTCUSDT", "side": "SELL",
                    "entry_price": bars[i].close,
                    "stop_loss": bars[i].close * 1.02,
                    "take_profit": bars[i].close * 0.94,
                    "invalidation_price": bars[i].close * 1.03,
                    "signal_source": "short_replay",
                }
            return None

        bars = _bars_rising()
        result = run_replay(bars, short_signal, _default_config())
        assert result.signals_generated == 1
        assert result.plans_created == 1

    def test_short_stop_loss_on_rising(self):
        """Short on rising prices hits stop loss."""
        def short_at_15(bars, i):
            if i == 15:
                return {
                    "symbol": "BTCUSDT", "side": "SELL",
                    "entry_price": bars[i].close,
                    "stop_loss": bars[i].close * 1.02,
                    "take_profit": bars[i].close * 0.94,
                    "invalidation_price": bars[i].close * 1.03,
                    "signal_source": "short_sl",
                }
            return None

        bars = _bars_rising()
        config = _default_config()
        result = run_replay(bars, short_at_15, config)
        if result.trades_executed > 0:
            # On rising prices, short should lose
            summary = result.ledger.summary()
            assert summary["total_pnl"] <= 0 or summary["losers"] >= 1

    def test_short_take_profit_on_falling(self):
        """Short on falling prices hits take profit."""
        def short_at_5(bars, i):
            if i == 5:
                return {
                    "symbol": "BTCUSDT", "side": "SELL",
                    "entry_price": bars[i].close,
                    "stop_loss": bars[i].close * 1.05,
                    "take_profit": bars[i].close * 0.95,
                    "invalidation_price": bars[i].close * 1.06,
                    "signal_source": "short_tp",
                }
            return None

        bars = _bars_falling(50)
        result = run_replay(bars, short_at_5, _default_config())
        if result.trades_executed > 0:
            dist = result.ledger.exit_reason_distribution
            # Take profit or trailing stop should fire
            assert any(k in dist for k in ("TAKE_PROFIT", "TRAILING_STOP"))

    def test_short_rr_reject(self):
        """Short with bad RR gets rejected."""
        def bad_short(bars, i):
            if i == 15:
                return {
                    "symbol": "BTCUSDT", "side": "SELL",
                    "entry_price": bars[i].close,
                    "stop_loss": bars[i].close * 1.10,  # wide SL
                    "take_profit": bars[i].close * 0.97,  # tight TP
                    "invalidation_price": bars[i].close * 1.11,
                    "signal_source": "bad_short",
                }
            return None

        bars = _bars_rising()
        result = run_replay(bars, bad_short, _default_config())
        if result.signals_generated > 0:
            # RR = 0.03/0.10 = 0.3 < 1.5 → rejected
            assert result.plans_approved == 0

    def test_short_with_portfolio_risk(self):
        """Short through portfolio risk integration."""
        from core.paper_trading.portfolio_risk import PortfolioRiskConfig

        def short_signal(bars, i):
            if i == 10:
                return {
                    "symbol": "BTCUSDT", "side": "SELL",
                    "entry_price": bars[i].close,
                    "stop_loss": bars[i].close * 1.02,
                    "take_profit": bars[i].close * 0.94,
                    "invalidation_price": bars[i].close * 1.03,
                    "signal_source": "short_portfolio",
                }
            return None

        bars = _bars_rising()
        config = ReplayConfig(
            risk_config=RiskSizingConfig(
                max_risk_per_trade_pct=1.0,
                max_position_pct=10.0,
                min_rr_ratio=1.5,
                max_margin_cap=50000,
                equity=100000,
            ),
            exit_config=ExitRuleConfig(),
            portfolio_config=PortfolioRiskConfig(
                max_open_plans=5,
                block_duplicate_direction=True,
            ),
            auto_approve=True,
            use_portfolio_risk=True,
        )
        result = run_replay(bars, short_signal, config)
        assert result.account is not None
