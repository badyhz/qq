"""Data source smoke test — verify readonly data source works, no network."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.data_source import DataSourceConfig, create_data_source
from core.paper_trading.fixture_adapter import FixtureDataSource
from core.paper_trading.snapshot_adapter import SnapshotAdapter


def main():
    print("=== Data Source Smoke Test ===\n")

    # Test 1: Fixture adapter
    print("1. Fixture adapter ...")
    config = DataSourceConfig(mode="fixture")
    source = create_data_source(config)
    assert source.source_name == "fixture"
    assert source.is_available() is False  # no fixture path
    bars = source.get_bars("BTCUSDT")
    assert bars == []
    snap = source.get_snapshot("BTCUSDT")
    assert snap is None
    print("   PASS")

    # Test 2: Snapshot adapter
    print("2. Snapshot adapter ...")
    config = DataSourceConfig(mode="snapshot")
    source = create_data_source(config)
    assert source.source_name == "snapshot"
    assert source.is_available() is True
    bars = source.get_bars("BTCUSDT")
    assert bars == []
    snap = source.get_snapshot("BTCUSDT")
    assert snap is not None
    assert snap.symbol == "BTCUSDT"
    assert snap.source == "skeleton"
    print("   PASS")

    # Test 3: Network disabled
    print("3. Network disabled ...")
    assert source.network_enabled is False
    print("   PASS")

    # Test 4: No account methods
    print("4. No account methods ...")
    forbidden = ["get_account", "get_balance", "get_position",
                 "submit_order", "place_order", "cancel_order"]
    for method in forbidden:
        assert not hasattr(source, method), f"Forbidden method: {method}"
    print("   PASS")

    # Test 5: Config switch
    print("5. Config switch ...")
    config_fixture = DataSourceConfig(mode="fixture")
    config_snapshot = DataSourceConfig(mode="snapshot")
    assert config_fixture.mode == "fixture"
    assert config_snapshot.mode == "snapshot"
    assert config_fixture.network_enabled is False
    assert config_snapshot.network_enabled is False
    print("   PASS")

    print("\n=== All Smoke Tests Passed ===")
    print("\nSafety:")
    print("- No network calls")
    print("- No secret reads")
    print("- No order paths")
    print("- No account access")
    return 0


if __name__ == "__main__":
    sys.exit(main())
