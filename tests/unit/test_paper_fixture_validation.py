"""Tests for fixture validation — empty and malformed fixtures."""
from __future__ import annotations

import os
import pytest

from core.paper_trading.risk_sizing import RiskSizingConfig
from core.paper_trading.exit_rules import ExitRuleConfig
from core.paper_trading.replay_engine import (
    ReplayBar, ReplayConfig, load_bars_from_fixture, run_replay,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "paper_trading")


def _noop_signal(bars, i):
    return None


def _default_config():
    return ReplayConfig(
        risk_config=RiskSizingConfig(),
        exit_config=ExitRuleConfig(),
        auto_approve=True,
    )


class TestFixtureValidation:
    def test_empty_fixture_loads(self):
        path = os.path.join(FIXTURE_DIR, "empty_sample.json")
        bars = load_bars_from_fixture(path)
        assert bars == []

    def test_empty_fixture_replay(self):
        path = os.path.join(FIXTURE_DIR, "empty_sample.json")
        bars = load_bars_from_fixture(path)
        result = run_replay(bars, _noop_signal, _default_config())
        assert result.bars_processed == 0
        assert result.signals_generated == 0
        assert result.trades_executed == 0

    def test_empty_fixture_ledger_empty(self):
        path = os.path.join(FIXTURE_DIR, "empty_sample.json")
        bars = load_bars_from_fixture(path)
        result = run_replay(bars, _noop_signal, _default_config())
        assert result.ledger.total_trades == 0
        summary = result.ledger.summary()
        assert summary["total_pnl"] == 0

    def test_malformed_fixture_raises(self):
        path = os.path.join(FIXTURE_DIR, "malformed_sample.json")
        with pytest.raises((ValueError, TypeError)):
            load_bars_from_fixture(path)

    def test_missing_fixture_raises(self):
        path = os.path.join(FIXTURE_DIR, "nonexistent_fixture.json")
        with pytest.raises(FileNotFoundError):
            load_bars_from_fixture(path)

    def test_empty_replay_with_signal(self):
        """Signal function on empty bars should not crash."""
        def signal_always(bars, i):
            return {"symbol": "BTC", "side": "BUY", "entry_price": 100,
                    "stop_loss": 90, "take_profit": 120, "invalidation_price": 85,
                    "signal_source": "test"}

        bars = []
        result = run_replay(bars, signal_always, _default_config())
        assert result.bars_processed == 0
        assert result.signals_generated == 0
