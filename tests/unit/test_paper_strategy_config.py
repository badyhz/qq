"""Tests for strategy config loader — safety validation and parsing."""
from __future__ import annotations

import os
import tempfile

import pytest
import yaml

from core.paper_trading.strategy_config import (
    load_strategy_config,
    StrategyLibrary,
    StrategyConfig,
    DataApiConfig,
    AlertConfig,
)


def _write_config(tmpdir: str, config: dict, filename: str = "strategies.yaml") -> str:
    path = os.path.join(tmpdir, filename)
    with open(path, "w") as f:
        yaml.dump(config, f)
    return path


def _base_config() -> dict:
    return {
        "version": 1,
        "default_mode": "paper",
        "default_alert": "feishu_payload_only",
        "data_apis": {
            "binance_usdm_klines": {
                "type": "binance_public_klines",
                "market": "usdm_futures",
                "readonly": True,
                "requires_secret": False,
                "allows_orders": False,
                "default_limit": 120,
            }
        },
        "strategies": {
            "test_strategy": {
                "enabled": True,
                "strategy_type": "macd_rebound_watch",
                "description": "Test strategy",
                "data_api": "binance_usdm_klines",
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "timeframes": ["5m", "15m"],
                "mode": "paper",
                "alert": {"feishu_payload": True, "auto_send": False},
            }
        },
    }


class TestLoadStrategyConfig:
    def test_loads_valid_config(self, tmp_path):
        path = _write_config(str(tmp_path), _base_config())
        lib = load_strategy_config(path)
        assert lib.version == 1
        assert lib.default_mode == "paper"
        assert "test_strategy" in lib.strategies
        assert lib.strategies["test_strategy"].enabled is True

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_strategy_config("/nonexistent/strategies.yaml")

    def test_enabled_disabled_split(self, tmp_path):
        config = _base_config()
        config["strategies"]["disabled_one"] = {
            "enabled": False,
            "strategy_type": "breakout_pullback_watch",
            "data_api": "binance_usdm_klines",
            "symbols": ["SOLUSDT"],
            "timeframes": ["1h"],
            "mode": "paper",
            "alert": {"feishu_payload": True, "auto_send": False},
        }
        path = _write_config(str(tmp_path), config)
        lib = load_strategy_config(path)
        assert "test_strategy" in lib.enabled_strategies
        assert "disabled_one" in lib.disabled_strategies
        assert len(lib.enabled_strategies) == 1
        assert len(lib.disabled_strategies) == 1


class TestSafetyValidation:
    def test_mode_must_be_paper(self, tmp_path):
        config = _base_config()
        config["strategies"]["test_strategy"]["mode"] = "live"
        path = _write_config(str(tmp_path), config)
        with pytest.raises(ValueError, match="mode=paper"):
            load_strategy_config(path)

    def test_auto_send_must_be_false(self, tmp_path):
        config = _base_config()
        config["strategies"]["test_strategy"]["alert"]["auto_send"] = True
        path = _write_config(str(tmp_path), config)
        with pytest.raises(ValueError, match="auto_send"):
            load_strategy_config(path)

    def test_data_api_must_be_readonly(self, tmp_path):
        config = _base_config()
        config["data_apis"]["binance_usdm_klines"]["readonly"] = False
        path = _write_config(str(tmp_path), config)
        with pytest.raises(ValueError, match="readonly"):
            load_strategy_config(path)

    def test_data_api_must_not_require_secret(self, tmp_path):
        config = _base_config()
        config["data_apis"]["binance_usdm_klines"]["requires_secret"] = True
        path = _write_config(str(tmp_path), config)
        with pytest.raises(ValueError, match="secret"):
            load_strategy_config(path)

    def test_data_api_must_not_allow_orders(self, tmp_path):
        config = _base_config()
        config["data_apis"]["binance_usdm_klines"]["allows_orders"] = True
        path = _write_config(str(tmp_path), config)
        with pytest.raises(ValueError, match="orders"):
            load_strategy_config(path)

    def test_unknown_data_api_raises(self, tmp_path):
        config = _base_config()
        config["strategies"]["test_strategy"]["data_api"] = "unknown_api"
        path = _write_config(str(tmp_path), config)
        with pytest.raises(ValueError, match="unknown data_api"):
            load_strategy_config(path)

    def test_empty_symbols_raises(self, tmp_path):
        config = _base_config()
        config["strategies"]["test_strategy"]["symbols"] = []
        path = _write_config(str(tmp_path), config)
        with pytest.raises(ValueError, match="symbol"):
            load_strategy_config(path)

    def test_empty_timeframes_raises(self, tmp_path):
        config = _base_config()
        config["strategies"]["test_strategy"]["timeframes"] = []
        path = _write_config(str(tmp_path), config)
        with pytest.raises(ValueError, match="timeframe"):
            load_strategy_config(path)


class TestStrategyFields:
    def test_symbols_preserved(self, tmp_path):
        path = _write_config(str(tmp_path), _base_config())
        lib = load_strategy_config(path)
        strat = lib.strategies["test_strategy"]
        assert "BTCUSDT" in strat.symbols
        assert "ETHUSDT" in strat.symbols

    def test_timeframes_preserved(self, tmp_path):
        path = _write_config(str(tmp_path), _base_config())
        lib = load_strategy_config(path)
        strat = lib.strategies["test_strategy"]
        assert "5m" in strat.timeframes
        assert "15m" in strat.timeframes

    def test_alert_config(self, tmp_path):
        path = _write_config(str(tmp_path), _base_config())
        lib = load_strategy_config(path)
        strat = lib.strategies["test_strategy"]
        assert strat.alert.feishu_payload is True
        assert strat.alert.auto_send is False

    def test_data_api_fields(self, tmp_path):
        path = _write_config(str(tmp_path), _base_config())
        lib = load_strategy_config(path)
        api = lib.data_apis["binance_usdm_klines"]
        assert api.readonly is True
        assert api.requires_secret is False
        assert api.allows_orders is False
        assert api.default_limit == 120
