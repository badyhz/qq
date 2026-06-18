"""Tests for data source interface — no network, no account, no orders."""
from __future__ import annotations

import pytest

from core.paper_trading.data_source import (
    MarketBar, MarketSnapshot, DataSourceConfig, DataSource, create_data_source,
)


class TestMarketBar:
    def test_create_bar(self):
        bar = MarketBar(timestamp=1000.0, open=100.0, high=110.0, low=90.0, close=105.0, volume=1000.0)
        assert bar.timestamp == 1000.0
        assert bar.open == 100.0
        assert bar.high == 110.0
        assert bar.low == 90.0
        assert bar.close == 105.0
        assert bar.volume == 1000.0

    def test_bar_is_readonly(self):
        bar = MarketBar(timestamp=1000.0, open=100.0, high=110.0, low=90.0, close=105.0, volume=1000.0)
        with pytest.raises(AttributeError):
            bar.open = 200.0

    def test_bar_with_symbol(self):
        bar = MarketBar(timestamp=1000.0, open=100.0, high=110.0, low=90.0, close=105.0, volume=1000.0,
                        symbol="BTCUSDT", timeframe="1h")
        assert bar.symbol == "BTCUSDT"
        assert bar.timeframe == "1h"


class TestMarketSnapshot:
    def test_create_snapshot(self):
        snap = MarketSnapshot(symbol="BTCUSDT", price=50000.0, timestamp=1000.0)
        assert snap.symbol == "BTCUSDT"
        assert snap.price == 50000.0

    def test_snapshot_is_readonly(self):
        snap = MarketSnapshot(symbol="BTCUSDT", price=50000.0, timestamp=1000.0)
        with pytest.raises(AttributeError):
            snap.price = 60000.0

    def test_snapshot_with_optional_fields(self):
        snap = MarketSnapshot(symbol="BTCUSDT", price=50000.0, timestamp=1000.0,
                              bid=49999.0, ask=50001.0, volume_24h=1000.0, source="test")
        assert snap.bid == 49999.0
        assert snap.ask == 50001.0
        assert snap.source == "test"


class TestDataSourceConfig:
    def test_default_config(self):
        config = DataSourceConfig()
        assert config.mode == "fixture"
        assert config.network_enabled is False

    def test_config_is_readonly(self):
        config = DataSourceConfig()
        with pytest.raises(AttributeError):
            config.mode = "live"

    def test_fixture_config(self):
        config = DataSourceConfig(mode="fixture", fixture_path="/tmp/test.json")
        assert config.mode == "fixture"
        assert config.fixture_path == "/tmp/test.json"


class TestDataSourceInterface:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            DataSource()


class TestCreateDataSource:
    def test_invalid_mode_raises(self):
        config = DataSourceConfig(mode="invalid")
        with pytest.raises(ValueError):
            create_data_source(config)

    def test_fixture_source_requires_adapter(self):
        config = DataSourceConfig(mode="fixture")
        with pytest.raises(ModuleNotFoundError):
            create_data_source(config)

    def test_snapshot_source_requires_adapter(self):
        config = DataSourceConfig(mode="snapshot")
        with pytest.raises(ModuleNotFoundError):
            create_data_source(config)
