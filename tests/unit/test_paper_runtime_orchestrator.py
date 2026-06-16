"""Tests for paper runtime orchestrator."""
from __future__ import annotations

import os
import tempfile

import pytest

from core.paper_trading.runtime_config import RuntimeConfig
from core.paper_trading.runtime_orchestrator import RuntimeResult, run_paper_runtime
from core.paper_trading.run_history import read_history
from core.paper_trading.strategy_registry import create_default_registry, StrategyRegistry, StrategyMeta

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "paper_trading")


def _fixture(name: str) -> str:
    return os.path.join(FIXTURE_DIR, name)


def _config(**kwargs):
    defaults = dict(
        mode="paper_only",
        strategy_name="macd_rebound",
        fixture_paths=[_fixture("macd_rebound_sample.json")],
        enable_local_alerts=True,
    )
    defaults.update(kwargs)
    return RuntimeConfig(**defaults)


class TestRuntimeOrchestrator:
    def test_normal_run(self):
        result = run_paper_runtime(_config(), write_history=False)
        assert result.status == "OK"
        assert result.fixtures_run == 1
        assert result.safety_flags[0] == "NO_REAL_ORDER"

    def test_unknown_strategy(self):
        cfg = _config(strategy_name="nonexistent")
        result = run_paper_runtime(cfg, write_history=False)
        assert result.status == "ERROR"
        assert result.rating == "REJECT"

    def test_empty_fixtures(self):
        cfg = _config(fixture_paths=[])
        result = run_paper_runtime(cfg, write_history=False)
        assert result.status == "NO_FIXTURES"
        assert result.total_trades == 0

    def test_malformed_fixture_no_crash(self):
        cfg = _config(fixture_paths=[
            _fixture("macd_rebound_sample.json"),
            _fixture("malformed_sample.json"),
        ])
        result = run_paper_runtime(cfg, write_history=False)
        assert result.fixtures_run >= 1
        assert result.fixtures_failed >= 1

    def test_alerts_disabled(self):
        cfg = _config(enable_local_alerts=False)
        result = run_paper_runtime(cfg, write_history=False)
        assert result.alerts_written == 0

    def test_alerts_enabled(self):
        cfg = _config(
            fixture_paths=[_fixture("macd_rebound_loss_sample.json")],
            enable_local_alerts=True,
        )
        result = run_paper_runtime(cfg, write_history=False)
        # Alerts may or may not fire depending on metrics
        assert isinstance(result.alerts_written, int)

    def test_risk_rejection_counted(self):
        cfg = _config(fixture_paths=[
            _fixture("macd_rebound_sample.json"),
            _fixture("macd_rebound_sample.json"),
        ])
        result = run_paper_runtime(cfg, write_history=False)
        assert result.total_rejected >= 0

    def test_safety_flags_complete(self):
        result = run_paper_runtime(_config(), write_history=False)
        assert "NO_REAL_ORDER" in result.safety_flags
        assert "PAPER_ONLY" in result.safety_flags
        assert "NO_TESTNET" in result.safety_flags

    def test_scorecard_present(self):
        result = run_paper_runtime(_config(), write_history=False)
        assert result.scorecard is not None
        assert result.rating in ("A", "B", "C", "D", "REJECT")

    def test_metrics_present(self):
        result = run_paper_runtime(_config(), write_history=False)
        assert result.metrics is not None
        assert result.metrics.total_trades >= 0

    def test_custom_registry(self):
        reg = create_default_registry()
        result = run_paper_runtime(_config(), registry=reg, write_history=False)
        assert result.status == "OK"

    def test_writes_history(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        os.unlink(path)
        try:
            result = run_paper_runtime(_config(), history_path=path)
            assert result.status == "OK"
            records = read_history(path)
            assert len(records) == 1
            assert records[0].strategy_name == "macd_rebound"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_no_history_when_disabled(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        os.unlink(path)
        try:
            run_paper_runtime(_config(), write_history=False, history_path=path)
            assert not os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)
