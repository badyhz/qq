"""Tests for strategy switchboard — job building and offline mode."""
from __future__ import annotations

import os
import py_compile

import pytest

from core.paper_trading.strategy_config import (
    StrategyLibrary, StrategyConfig, DataApiConfig, AlertConfig,
)
from core.paper_trading.strategy_switchboard import (
    build_jobs, run_switchboard_offline, SwitchboardResult, StrategyJob,
)


def _make_library(enabled_count=2, disabled_count=1) -> StrategyLibrary:
    """Create a test strategy library."""
    api = DataApiConfig(
        name="binance_usdm_klines", api_type="binance_public_klines",
        market="usdm_futures", readonly=True, requires_secret=False,
        allows_orders=False, default_limit=120,
    )

    strategies = {}
    for i in range(enabled_count):
        strategies[f"enabled_{i}"] = StrategyConfig(
            strategy_id=f"enabled_{i}", strategy_type="macd_rebound_watch",
            description=f"Enabled strategy {i}", enabled=True,
            data_api="binance_usdm_klines",
            symbols=["BTCUSDT", "ETHUSDT"], timeframes=["5m", "15m"],
            mode="paper", alert=AlertConfig(feishu_payload=True, auto_send=False),
        )
    for i in range(disabled_count):
        strategies[f"disabled_{i}"] = StrategyConfig(
            strategy_id=f"disabled_{i}", strategy_type="breakout_pullback_watch",
            description=f"Disabled strategy {i}", enabled=False,
            data_api="binance_usdm_klines",
            symbols=["SOLUSDT"], timeframes=["1h"],
            mode="paper", alert=AlertConfig(feishu_payload=True, auto_send=False),
        )

    enabled = {k: v for k, v in strategies.items() if v.enabled}
    disabled = {k: v for k, v in strategies.items() if not v.enabled}

    return StrategyLibrary(
        version=1, default_mode="paper", default_alert="feishu_payload_only",
        data_apis={"binance_usdm_klines": api},
        strategies=strategies, enabled_strategies=enabled, disabled_strategies=disabled,
    )


class TestBuildJobs:
    def test_jobs_from_enabled_only(self):
        lib = _make_library(enabled_count=2, disabled_count=1)
        jobs = build_jobs(lib)
        # 2 strategies × 2 symbols × 2 timeframes = 8 jobs
        assert len(jobs) == 8

    def test_no_jobs_from_disabled(self):
        lib = _make_library(enabled_count=1, disabled_count=2)
        jobs = build_jobs(lib)
        # Only enabled_0: 2 symbols × 2 tf = 4 jobs
        for job in jobs:
            assert job.strategy_id == "enabled_0"

    def test_job_fields(self):
        lib = _make_library(enabled_count=1, disabled_count=0)
        jobs = build_jobs(lib)
        assert len(jobs) == 4
        for job in jobs:
            assert job.strategy_id == "enabled_0"
            assert job.strategy_type == "macd_rebound_watch"
            assert job.data_api == "binance_usdm_klines"
            assert job.symbol in ("BTCUSDT", "ETHUSDT")
            assert job.timeframe in ("5m", "15m")


class TestRunSwitchboardOffline:
    def test_offline_produces_candidates(self):
        lib = _make_library(enabled_count=1, disabled_count=0)
        result = run_switchboard_offline(lib, "2026-06-18")
        assert result.candidate_count == 4
        assert result.success_count == 4
        assert result.fail_count == 0

    def test_offline_mode_field(self):
        lib = _make_library(enabled_count=1, disabled_count=0)
        result = run_switchboard_offline(lib, "2026-06-18")
        assert result.mode == "offline_sample"

    def test_offline_enabled_disabled_lists(self):
        lib = _make_library(enabled_count=2, disabled_count=1)
        result = run_switchboard_offline(lib, "2026-06-18")
        assert "enabled_0" in result.enabled_strategies
        assert "enabled_1" in result.enabled_strategies
        assert "disabled_0" in result.disabled_strategies

    def test_offline_candidate_directions(self):
        lib = _make_library(enabled_count=1, disabled_count=0)
        result = run_switchboard_offline(lib, "2026-06-18")
        for c in result.candidates:
            assert c.direction in ("LONG_OBSERVE", "SHORT_OBSERVE", "NO_TRADE")


class TestSwitchboardSafety:
    def test_no_order_words_in_module(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "strategy_switchboard.py")
        with open(module_path) as f:
            content = f.read()
        forbidden = ["submit_order", "place_order", "cancel_order", "execute_trade"]
        for word in forbidden:
            assert word not in content, f"forbidden word '{word}' in module"

    def test_no_secret_reads(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "strategy_switchboard.py")
        with open(module_path) as f:
            content = f.read()
        assert "os.environ" not in content
        assert "os.getenv" not in content
        assert "API_KEY" not in content
        assert "API_SECRET" not in content

    def test_module_compiles(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "strategy_switchboard.py")
        py_compile.compile(module_path, doraise=True)
