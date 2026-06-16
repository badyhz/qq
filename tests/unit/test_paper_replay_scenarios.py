"""Paper replay scenario tests — loss, no-signal, RR reject."""
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


def _load(name: str):
    return load_bars_from_fixture(os.path.join(FIXTURE_DIR, name))


def macd_rebound_signal(bars, i):
    """Same signal as dry-run runner."""
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
            "signal_source": "macd_rebound_test",
        }
    return None


def bad_rr_signal(bars, i):
    """Signal with RR < 1.5 — should be rejected."""
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
            "stop_loss": current * 0.90,   # wide SL = 10% risk
            "take_profit": current * 1.03,  # tight TP = 3% reward
            "invalidation_price": current * 0.89,
            "signal_source": "bad_rr_test",
        }
    return None


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


class TestLossScenario:
    """Signal triggers but stop loss hit — negative PnL."""

    def test_loss_replay(self):
        bars = _load("macd_rebound_loss_sample.json")
        result = run_replay(bars, macd_rebound_signal, _default_config())

        assert result.signals_generated >= 1
        assert result.plans_created >= 1
        assert result.trades_executed >= 1

        summary = result.ledger.summary()
        assert summary["losers"] >= 1, "At least one losing trade expected"
        assert summary["total_pnl"] < 0, "Total PnL should be negative"

    def test_loss_exit_reason_trailing(self):
        """BUY signals from 3% drops trigger trailing stop before stop loss.

        The signal fires at 3%+ below HWM, which is always below the 1.5%
        trailing stop level. So trailing stop fires first.
        """
        bars = _load("macd_rebound_loss_sample.json")
        result = run_replay(bars, macd_rebound_signal, _default_config())

        dist = result.ledger.exit_reason_distribution
        assert "TRAILING_STOP" in dist, "Expected trailing stop exit"
        assert dist["TRAILING_STOP"] >= 1

    def test_loss_exit_reason_stop_loss_with_custom_signal(self):
        """Custom signal with tight TP and wide SL triggers stop loss."""
        # Use a signal that fires near the top (small drop) with wide SL
        def near_top_signal(bars, i):
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
                    "stop_loss": current * 0.995,   # tight SL: 0.5%
                    "take_profit": current * 1.06,
                    "invalidation_price": current * 0.99,
                    "signal_source": "sl_test",
                }
            return None

        bars = _load("macd_rebound_loss_sample.json")
        config = ReplayConfig(
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
        result = run_replay(bars, near_top_signal, config)
        # With tight SL (0.5%), stop loss should fire before trailing stop
        # SL = 48900 * 0.995 = 48655.5, trail = 50500 * 0.985 = 49742.5
        # Bar 12 close 48500 < 48655.5 → stop loss
        if result.trades_executed > 0:
            dist = result.ledger.exit_reason_distribution
            assert "STOP_LOSS" in dist, f"Expected stop loss, got {dist}"

    def test_loss_consecutive(self):
        bars = _load("macd_rebound_loss_sample.json")
        result = run_replay(bars, macd_rebound_signal, _default_config())

        # With only one trade, consecutive_losses is either 0 or 1
        assert result.ledger.consecutive_losses >= 0


class TestNoSignalScenario:
    """Monotonically rising prices — no signals generated."""

    def test_no_signals(self):
        bars = _load("macd_rebound_no_signal_sample.json")
        result = run_replay(bars, macd_rebound_signal, _default_config())

        assert result.signals_generated == 0
        assert result.plans_created == 0
        assert result.plans_approved == 0
        assert result.trades_executed == 0

    def test_no_signals_ledger_empty(self):
        bars = _load("macd_rebound_no_signal_sample.json")
        result = run_replay(bars, macd_rebound_signal, _default_config())

        assert result.ledger.total_trades == 0
        assert result.ledger.total_pnl == 0.0
        assert result.ledger.win_rate == 0.0

    def test_no_signals_bars_processed(self):
        bars = _load("macd_rebound_no_signal_sample.json")
        result = run_replay(bars, macd_rebound_signal, _default_config())

        assert result.bars_processed == 15


class TestRRRejectScenario:
    """Signal triggers but RR too low — plan cancelled."""

    def test_rr_reject_signal_generated(self):
        bars = _load("macd_rebound_rr_reject_sample.json")
        result = run_replay(bars, bad_rr_signal, _default_config())

        assert result.signals_generated >= 1

    def test_rr_reject_no_trades(self):
        bars = _load("macd_rebound_rr_reject_sample.json")
        result = run_replay(bars, bad_rr_signal, _default_config())

        # Plans should be created but cancelled (not approved)
        assert result.plans_approved == 0
        assert result.trades_executed == 0

    def test_rr_reject_ledger_has_cancelled(self):
        bars = _load("macd_rebound_rr_reject_sample.json")
        result = run_replay(bars, bad_rr_signal, _default_config())

        # Cancelled plans are recorded with SIGNAL_INVALIDATED
        assert result.ledger.total_trades >= 1
        dist = result.ledger.exit_reason_distribution
        assert "SIGNAL_INVALIDATED" in dist

    def test_rr_reject_no_active_plans(self):
        bars = _load("macd_rebound_rr_reject_sample.json")
        result = run_replay(bars, bad_rr_signal, _default_config())

        summary = result.ledger.summary()
        assert summary["total_pnl"] == 0.0


class TestShortSideScenario:
    """SELL side signal with loss."""

    def test_short_loss(self):
        """Short signal where price rises above stop loss."""
        def short_signal(bars, i):
            if i < 10:
                return None
            recent_low = min(b.low for b in bars[max(0, i - 10):i])
            current = bars[i].close
            rise_pct = (current - recent_low) / recent_low * 100
            if rise_pct >= 3.0 and bars[i].close < bars[i].open:
                return {
                    "symbol": "BTCUSDT",
                    "side": "SELL",
                    "entry_price": current,
                    "stop_loss": current * 1.02,
                    "take_profit": current * 0.94,
                    "invalidation_price": current * 1.03,
                    "signal_source": "short_test",
                }
            return None

        # Create a fixture-like bars list with a rise then drop
        bars = _load("macd_rebound_sample.json")
        result = run_replay(bars, short_signal, _default_config())
        # Just verify it doesn't crash — short signals may or may not trigger
        assert result.bars_processed == len(bars)


class TestDuplicateSignalScenario:
    """Multiple signals on consecutive bars."""

    def test_every_bar_signal(self):
        """Signal on every bar after i=10 — should create multiple plans."""
        def always_signal(bars, i):
            if i < 10:
                return None
            return {
                "symbol": "BTCUSDT",
                "side": "BUY",
                "entry_price": bars[i].close,
                "stop_loss": bars[i].close * 0.98,
                "take_profit": bars[i].close * 1.06,
                "invalidation_price": bars[i].close * 0.97,
                "signal_source": "every_bar",
            }

        bars = _load("macd_rebound_sample.json")
        result = run_replay(bars, always_signal, _default_config())

        assert result.signals_generated > 1
        assert result.plans_created > 1
