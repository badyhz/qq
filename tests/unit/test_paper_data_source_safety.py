"""Safety tests for data source — no network, no secret, no order."""
from __future__ import annotations

import ast
import os

import pytest

PAPER_TRADING_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "core", "paper_trading")

DATA_SOURCE_FILES = [
    "data_source.py",
    "fixture_adapter.py",
    "snapshot_adapter.py",
]

FORBIDDEN_IMPORTS = [
    "requests", "httpx", "aiohttp", "websocket", "urllib",
]

FORBIDDEN_PATTERNS = [
    "API_KEY", "API_SECRET", ".env",
    "submit_order", "place_order", "execute_trade",
    "cancel_order", "close_position",
    "get_account", "get_balance", "get_position",
]


class TestDataSourceNoNetworkImports:
    @pytest.mark.parametrize("filename", DATA_SOURCE_FILES)
    def test_no_network_imports(self, filename):
        filepath = os.path.join(PAPER_TRADING_DIR, filename)
        with open(filepath) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in FORBIDDEN_IMPORTS, \
                        f"{filename}: forbidden import {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS, \
                    f"{filename}: forbidden import {node.module}"


class TestDataSourceNoForbiddenPatterns:
    @pytest.mark.parametrize("filename", DATA_SOURCE_FILES)
    def test_no_forbidden_patterns(self, filename):
        filepath = os.path.join(PAPER_TRADING_DIR, filename)
        with open(filepath) as f:
            content = f.read()
        for pattern in FORBIDDEN_PATTERNS:
            assert pattern not in content, f"{filename}: forbidden pattern '{pattern}'"


class TestDataSourceNoSecretReads:
    @pytest.mark.parametrize("filename", DATA_SOURCE_FILES)
    def test_no_os_environ(self, filename):
        filepath = os.path.join(PAPER_TRADING_DIR, filename)
        with open(filepath) as f:
            content = f.read()
        assert "os.environ" not in content, f"{filename}: os.environ found"
        assert "os.getenv" not in content, f"{filename}: os.getenv found"


class TestDataSourceNoAccountMethods:
    def test_data_source_has_no_account_methods(self):
        from core.paper_trading.data_source import DataSource
        forbidden = ["get_account", "get_balance", "get_position",
                     "submit_order", "place_order", "cancel_order"]
        for method in forbidden:
            assert not hasattr(DataSource, method), f"DataSource has forbidden method: {method}"

    def test_fixture_adapter_has_no_account_methods(self):
        from core.paper_trading.fixture_adapter import FixtureDataSource
        from core.paper_trading.data_source import DataSourceConfig
        config = DataSourceConfig(mode="fixture")
        adapter = FixtureDataSource(config)
        forbidden = ["get_account", "get_balance", "get_position",
                     "submit_order", "place_order", "cancel_order"]
        for method in forbidden:
            assert not hasattr(adapter, method), f"FixtureDataSource has forbidden method: {method}"

    def test_snapshot_adapter_has_no_account_methods(self):
        from core.paper_trading.snapshot_adapter import SnapshotAdapter
        from core.paper_trading.data_source import DataSourceConfig
        config = DataSourceConfig(mode="snapshot")
        adapter = SnapshotAdapter(config)
        forbidden = ["get_account", "get_balance", "get_position",
                     "submit_order", "place_order", "cancel_order"]
        for method in forbidden:
            assert not hasattr(adapter, method), f"SnapshotAdapter has forbidden method: {method}"
