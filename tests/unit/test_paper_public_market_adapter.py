"""Tests for public market adapter — mock transport, no real network."""
from __future__ import annotations

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from core.paper_trading.data_source import DataSourceConfig, MarketBar
from core.paper_trading.public_market_adapter import (
    BinancePublicKlineAdapter, _validate_symbol, _validate_interval, _parse_kline,
    DEFAULT_BASE_URL, DEFAULT_TIMEOUT, VALID_INTERVALS,
)


class TestValidateSymbol:
    def test_valid_symbol(self):
        assert _validate_symbol("BTCUSDT") is True
        assert _validate_symbol("ETHUSDT") is True
        assert _validate_symbol("BNBUSDT") is True

    def test_invalid_symbol(self):
        assert _validate_symbol("") is False
        assert _validate_symbol("BTC") is False
        assert _validate_symbol("btcusdt") is False
        assert _validate_symbol("BTCUSD") is False
        assert _validate_symbol("123USDT") is True  # digits allowed


class TestValidateInterval:
    def test_valid_interval(self):
        for interval in VALID_INTERVALS:
            assert _validate_interval(interval) is True

    def test_invalid_interval(self):
        assert _validate_interval("") is False
        assert _validate_interval("2h") is False
        assert _validate_interval("1w") is False


class TestParseKline:
    def test_valid_kline(self):
        raw = [1000000, "50000.0", "51000.0", "49000.0", "50500.0", "100.0", 1000600]
        bar = _parse_kline(raw)
        assert bar is not None
        assert bar.open == 50000.0
        assert bar.high == 51000.0
        assert bar.low == 49000.0
        assert bar.close == 50500.0
        assert bar.volume == 100.0

    def test_short_kline(self):
        raw = [1000000, "50000.0"]
        bar = _parse_kline(raw)
        assert bar is None

    def test_invalid_kline(self):
        raw = [1000000, "not_a_number", "51000.0", "49000.0", "50500.0", "100.0"]
        bar = _parse_kline(raw)
        assert bar is None


class TestBinancePublicKlineAdapter:
    def test_source_name(self):
        config = DataSourceConfig(mode="snapshot", network_enabled=False)
        adapter = BinancePublicKlineAdapter(config)
        assert adapter.source_name == "binance_public"

    def test_network_disabled(self):
        config = DataSourceConfig(mode="snapshot", network_enabled=False)
        adapter = BinancePublicKlineAdapter(config)
        assert adapter.network_enabled is False

    def test_get_bars_offline(self):
        config = DataSourceConfig(mode="snapshot", network_enabled=False)
        adapter = BinancePublicKlineAdapter(config)
        bars = adapter.get_bars("BTCUSDT")
        assert bars == []

    def test_get_bars_invalid_symbol(self):
        config = DataSourceConfig(mode="snapshot", network_enabled=True)
        adapter = BinancePublicKlineAdapter(config)
        bars = adapter.get_bars("invalid")
        assert bars == []

    def test_get_bars_invalid_interval(self):
        config = DataSourceConfig(mode="snapshot", network_enabled=True)
        adapter = BinancePublicKlineAdapter(config)
        bars = adapter.get_bars("BTCUSDT", timeframe="2h")
        assert bars == []

    @patch("core.paper_trading.public_market_adapter.urlopen")
    def test_get_bars_mock_success(self, mock_urlopen):
        mock_data = [
            [1000000, "50000.0", "51000.0", "49000.0", "50500.0", "100.0", 1000600, 0, 0, 0, 0, 0],
            [1000600, "50500.0", "52000.0", "50000.0", "51500.0", "120.0", 1001200, 0, 0, 0, 0, 0],
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        config = DataSourceConfig(mode="snapshot", network_enabled=True)
        adapter = BinancePublicKlineAdapter(config)
        bars = adapter.get_bars("BTCUSDT", timeframe="1h", limit=2)
        assert len(bars) == 2
        assert bars[0].symbol == "BTCUSDT"
        assert bars[0].open == 50000.0

    @patch("core.paper_trading.public_market_adapter.urlopen")
    def test_get_bars_mock_error(self, mock_urlopen):
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("timeout")

        config = DataSourceConfig(mode="snapshot", network_enabled=True)
        adapter = BinancePublicKlineAdapter(config, timeout=1)
        bars = adapter.get_bars("BTCUSDT")
        assert bars == []

    @patch("core.paper_trading.public_market_adapter.urlopen")
    def test_get_snapshot_mock(self, mock_urlopen):
        mock_data = [
            [1000000, "50000.0", "51000.0", "49000.0", "50500.0", "100.0", 1000600, 0, 0, 0, 0, 0],
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        config = DataSourceConfig(mode="snapshot", network_enabled=True)
        adapter = BinancePublicKlineAdapter(config)
        snap = adapter.get_snapshot("BTCUSDT")
        assert snap is not None
        assert snap.symbol == "BTCUSDT"
        assert snap.price == 50500.0

    def test_no_account_methods(self):
        config = DataSourceConfig(mode="snapshot", network_enabled=False)
        adapter = BinancePublicKlineAdapter(config)
        assert not hasattr(adapter, "get_account")
        assert not hasattr(adapter, "get_balance")
        assert not hasattr(adapter, "submit_order")
        assert not hasattr(adapter, "place_order")
        assert not hasattr(adapter, "cancel_order")


class TestPublicMarketAdapterSafety:
    def test_no_secret_reads(self):
        import ast
        module_path = os.path.join(os.path.dirname(__file__), "..", "..", "core", "paper_trading", "public_market_adapter.py")
        with open(module_path) as f:
            content = f.read()
        assert "API_KEY" not in content
        assert "API_SECRET" not in content
        assert ".env" not in content
        assert "os.environ" not in content
        assert "os.getenv" not in content

    def test_no_order_patterns(self):
        import ast
        module_path = os.path.join(os.path.dirname(__file__), "..", "..", "core", "paper_trading", "public_market_adapter.py")
        with open(module_path) as f:
            content = f.read()
        assert "submit_order" not in content
        assert "place_order" not in content
        assert "execute_trade" not in content
        assert "cancel_order" not in content
        assert "close_position" not in content

    def test_no_websocket(self):
        import ast
        module_path = os.path.join(os.path.dirname(__file__), "..", "..", "core", "paper_trading", "public_market_adapter.py")
        with open(module_path) as f:
            tree = ast.parse(f.read())
        forbidden = {"requests", "httpx", "aiohttp", "websocket"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden

    def test_only_urllib(self):
        import ast
        module_path = os.path.join(os.path.dirname(__file__), "..", "..", "core", "paper_trading", "public_market_adapter.py")
        with open(module_path) as f:
            tree = ast.parse(f.read())
        allowed_prefixes = ("urllib", "core.", "__future__", "typing")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert any(node.module.startswith(p) for p in allowed_prefixes), \
                    f"Unexpected import: {node.module}"
