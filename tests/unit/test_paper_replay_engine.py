"""Tests for paper replay engine."""
from __future__ import annotations
import pytest
import os
from core.paper_trading.order_plan import OrderSide, OrderStatus
from core.paper_trading.replay_engine import (
    ReplayBar, ReplayConfig, ReplayResult, load_bars_from_fixture, run_replay,
)
from core.paper_trading.risk_sizing import RiskSizingConfig
from core.paper_trading.exit_rules import ExitRuleConfig


FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "paper_trading",
    "macd_rebound_sample.json",
)


def _sample_bars():
    return [
        ReplayBar("T1", 50000, 50500, 49800, 50200, 100),
        ReplayBar("T2", 50200, 50800, 50000, 50600, 120),
        ReplayBar("T3", 50600, 51200, 50400, 51000, 150),
        ReplayBar("T4", 51000, 51100, 50200, 50300, 130),
        ReplayBar("T5", 50300, 50500, 49500, 49600, 180),
    ]


def _no_signal_fn(bars, i):
    return None


def _simple_signal_fn(bars, i):
    """Generate a BUY signal every 5 bars."""
    if i > 0 and i % 5 == 0:
        return {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "entry_price": bars[i].close,
            "stop_loss": bars[i].close * 0.98,
            "take_profit": bars[i].close * 1.06,
            "signal_source": "test",
        }
    return None


class TestReplayBar:
    def test_bar_creation(self):
        bar = ReplayBar("T1", 50000, 50500, 49800, 50200, 100)
        assert bar.timestamp == "T1"
        assert bar.open == 50000
        assert bar.close == 50200


class TestLoadBars:
    def test_load_fixture(self):
        if not os.path.exists(FIXTURE_PATH):
            pytest.skip("Fixture not found")
        bars = load_bars_from_fixture(FIXTURE_PATH)
        assert len(bars) == 30
        assert bars[0].open == 50000

    def test_fixture_has_required_fields(self):
        if not os.path.exists(FIXTURE_PATH):
            pytest.skip("Fixture not found")
        bars = load_bars_from_fixture(FIXTURE_PATH)
        for bar in bars:
            assert bar.open > 0
            assert bar.high >= bar.open
            assert bar.low <= bar.open
            assert bar.close > 0


class TestRunReplay:
    def test_no_signals(self):
        result = run_replay(_sample_bars(), _no_signal_fn, ReplayConfig())
        assert result.bars_processed == 5
        assert result.signals_generated == 0
        assert result.plans_created == 0
        assert result.trades_executed == 0

    def test_with_signals(self):
        result = run_replay(_sample_bars(), _simple_signal_fn, ReplayConfig())
        assert result.bars_processed == 5
        assert result.signals_generated == 0  # i=5 doesn't exist in 5 bars

    def test_signal_at_bar_zero_not_generated(self):
        """Signal function checks i > 0, so bar 0 should not generate."""
        result = run_replay(_sample_bars(), _simple_signal_fn, ReplayConfig())
        assert result.signals_generated == 0

    def test_replay_result_type(self):
        result = run_replay(_sample_bars(), _no_signal_fn, ReplayConfig())
        assert isinstance(result, ReplayResult)

    def test_ledger_empty_when_no_signals(self):
        result = run_replay(_sample_bars(), _no_signal_fn, ReplayConfig())
        assert result.ledger.total_trades == 0

    def test_fixture_replay(self):
        if not os.path.exists(FIXTURE_PATH):
            pytest.skip("Fixture not found")
        bars = load_bars_from_fixture(FIXTURE_PATH)
        result = run_replay(bars, _simple_signal_fn, ReplayConfig())
        assert result.bars_processed == 30
        assert result.ledger is not None
