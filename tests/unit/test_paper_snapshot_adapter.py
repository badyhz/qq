"""Tests for snapshot adapter — skeleton only, no network."""
from __future__ import annotations

import pytest

from core.paper_trading.data_source import DataSourceConfig
from core.paper_trading.snapshot_adapter import SnapshotAdapter


class TestSnapshotAdapter:
    def test_source_name(self):
        config = DataSourceConfig(mode="snapshot")
        adapter = SnapshotAdapter(config)
        assert adapter.source_name == "snapshot"

    def test_is_available(self):
        config = DataSourceConfig(mode="snapshot")
        adapter = SnapshotAdapter(config)
        assert adapter.is_available() is True

    def test_network_disabled(self):
        config = DataSourceConfig(mode="snapshot")
        adapter = SnapshotAdapter(config)
        assert adapter.network_enabled is False

    def test_get_bars_empty(self):
        config = DataSourceConfig(mode="snapshot")
        adapter = SnapshotAdapter(config)
        bars = adapter.get_bars("BTCUSDT")
        assert bars == []

    def test_get_snapshot_returns_skeleton(self):
        config = DataSourceConfig(mode="snapshot")
        adapter = SnapshotAdapter(config)
        snap = adapter.get_snapshot("BTCUSDT")
        assert snap is not None
        assert snap.symbol == "BTCUSDT"
        assert snap.price == 0.0
        assert snap.source == "skeleton"

    def test_no_network_imports(self):
        """Verify no network library imports in module."""
        import ast
        import os
        module_path = os.path.join(os.path.dirname(__file__), "..", "..", "core", "paper_trading", "snapshot_adapter.py")
        with open(module_path) as f:
            tree = ast.parse(f.read())
        forbidden = {"requests", "httpx", "aiohttp", "websocket", "urllib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, f"Forbidden import: {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden, f"Forbidden import: {node.module}"

    def test_no_account_methods(self):
        config = DataSourceConfig(mode="snapshot")
        adapter = SnapshotAdapter(config)
        assert not hasattr(adapter, "get_account")
        assert not hasattr(adapter, "get_balance")
        assert not hasattr(adapter, "get_position")
        assert not hasattr(adapter, "submit_order")
        assert not hasattr(adapter, "place_order")
        assert not hasattr(adapter, "cancel_order")
