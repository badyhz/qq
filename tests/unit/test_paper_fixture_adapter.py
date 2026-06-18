"""Tests for fixture data source adapter — no network."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from core.paper_trading.data_source import DataSourceConfig
from core.paper_trading.fixture_adapter import FixtureDataSource


@pytest.fixture
def sample_fixture():
    """Create a temporary fixture file."""
    data = [
        {"timestamp": 1000, "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000},
        {"timestamp": 2000, "open": 105, "high": 115, "low": 95, "close": 110, "volume": 1200},
        {"timestamp": 3000, "open": 110, "high": 120, "low": 100, "close": 115, "volume": 1500},
    ]
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump(data, f)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def empty_fixture():
    """Create an empty fixture file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump([], f)
        path = f.name
    yield path
    os.unlink(path)


class TestFixtureDataSource:
    def test_source_name(self):
        config = DataSourceConfig(mode="fixture")
        source = FixtureDataSource(config)
        assert source.source_name == "fixture"

    def test_is_available_with_path(self, sample_fixture):
        config = DataSourceConfig(mode="fixture", fixture_path=sample_fixture)
        source = FixtureDataSource(config)
        assert source.is_available() is True

    def test_is_available_no_path(self):
        config = DataSourceConfig(mode="fixture")
        source = FixtureDataSource(config)
        assert source.is_available() is False

    def test_is_available_missing_file(self):
        config = DataSourceConfig(mode="fixture", fixture_path="/tmp/nonexistent.json")
        source = FixtureDataSource(config)
        assert source.is_available() is False

    def test_get_bars(self, sample_fixture):
        config = DataSourceConfig(mode="fixture", fixture_path=sample_fixture)
        source = FixtureDataSource(config)
        bars = source.get_bars("BTCUSDT")
        assert len(bars) == 3
        assert bars[0].open == 100.0
        assert bars[0].close == 105.0
        assert bars[0].symbol == "BTCUSDT"

    def test_get_bars_with_limit(self, sample_fixture):
        config = DataSourceConfig(mode="fixture", fixture_path=sample_fixture)
        source = FixtureDataSource(config)
        bars = source.get_bars("BTCUSDT", limit=2)
        assert len(bars) == 2

    def test_get_bars_empty_fixture(self, empty_fixture):
        config = DataSourceConfig(mode="fixture", fixture_path=empty_fixture)
        source = FixtureDataSource(config)
        bars = source.get_bars("BTCUSDT")
        assert len(bars) == 0

    def test_get_bars_no_file(self):
        config = DataSourceConfig(mode="fixture")
        source = FixtureDataSource(config)
        bars = source.get_bars("BTCUSDT")
        assert len(bars) == 0

    def test_get_snapshot(self, sample_fixture):
        config = DataSourceConfig(mode="fixture", fixture_path=sample_fixture)
        source = FixtureDataSource(config)
        snap = source.get_snapshot("BTCUSDT")
        assert snap is not None
        assert snap.symbol == "BTCUSDT"
        assert snap.price == 115.0
        assert snap.source == "fixture"

    def test_get_snapshot_empty(self, empty_fixture):
        config = DataSourceConfig(mode="fixture", fixture_path=empty_fixture)
        source = FixtureDataSource(config)
        snap = source.get_snapshot("BTCUSDT")
        assert snap is None

    def test_no_account_methods(self, sample_fixture):
        config = DataSourceConfig(mode="fixture", fixture_path=sample_fixture)
        source = FixtureDataSource(config)
        assert not hasattr(source, "get_account")
        assert not hasattr(source, "get_balance")
        assert not hasattr(source, "get_position")
        assert not hasattr(source, "submit_order")
        assert not hasattr(source, "place_order")
