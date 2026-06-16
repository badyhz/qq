"""Tests for paper runtime config."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from core.paper_trading.runtime_config import (
    RuntimeConfig, default_config, load_config_from_dict, load_config_from_json,
)


class TestRuntimeConfig:
    def test_default_config(self):
        cfg = default_config()
        assert cfg.mode == "paper_only"
        assert cfg.strategy_name == "macd_rebound"
        assert cfg.max_risk_per_trade_pct == 1.0

    def test_json_load(self):
        data = {
            "mode": "paper_only",
            "strategy_name": "macd_rebound",
            "fixture_paths": ["a.json"],
            "max_risk_per_trade_pct": 2.0,
        }
        cfg = load_config_from_dict(data)
        assert cfg.strategy_name == "macd_rebound"
        assert cfg.fixture_paths == ["a.json"]
        assert cfg.max_risk_per_trade_pct == 2.0

    def test_json_file_load(self):
        data = {"mode": "paper_only", "strategy_name": "test"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            cfg = load_config_from_json(path)
            assert cfg.strategy_name == "test"
        finally:
            os.unlink(path)

    def test_live_mode_rejected(self):
        with pytest.raises(ValueError, match="paper_only"):
            RuntimeConfig(mode="live")

    def test_testnet_mode_rejected(self):
        with pytest.raises(ValueError, match="paper_only"):
            RuntimeConfig(mode="testnet")

    def test_empty_strategy_rejected(self):
        with pytest.raises(ValueError, match="strategy_name"):
            RuntimeConfig(strategy_name="")

    def test_bad_risk_pct_rejected(self):
        with pytest.raises(ValueError, match="max_risk_per_trade_pct"):
            RuntimeConfig(max_risk_per_trade_pct=0)
        with pytest.raises(ValueError, match="max_risk_per_trade_pct"):
            RuntimeConfig(max_risk_per_trade_pct=200)

    def test_bad_position_pct_rejected(self):
        with pytest.raises(ValueError, match="max_position_pct"):
            RuntimeConfig(max_position_pct=0)

    def test_bad_rr_rejected(self):
        with pytest.raises(ValueError, match="min_rr_ratio"):
            RuntimeConfig(min_rr_ratio=0)

    def test_no_env_reads(self):
        """Config must not read environment variables."""
        import core.paper_trading.runtime_config as mod
        source = open(mod.__file__).read()
        assert "os.environ" not in source
        assert "getenv" not in source

    def test_no_secret_patterns(self):
        """Config must not contain secret-related strings."""
        import core.paper_trading.runtime_config as mod
        source = open(mod.__file__).read().lower()
        for pattern in ["api_key", "api_secret", "password", "token"]:
            assert pattern not in source

    def test_frozen(self):
        cfg = default_config()
        with pytest.raises(AttributeError):
            cfg.mode = "live"  # type: ignore

    def test_default_alerts_enabled(self):
        cfg = default_config()
        assert cfg.enable_local_alerts is True
        assert cfg.enable_html_report is True
