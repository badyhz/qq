from __future__ import annotations

import pytest

from scripts.run_preflight_check import run_preflight_bundle, validate_preflight_mode


def test_validate_preflight_mode_rejects_live_mode() -> None:
    issues = validate_preflight_mode(mode="live", environment="testnet", connector_enabled=True)
    assert "mode_live_blocked" in issues


def test_validate_preflight_mode_accepts_testnet_connector() -> None:
    issues = validate_preflight_mode(mode="testnet", environment="testnet", connector_enabled=True)
    assert issues == []


def test_validate_preflight_mode_accepts_sandbox_connector() -> None:
    issues = validate_preflight_mode(mode="testnet", environment="sandbox", connector_enabled=True)
    assert issues == []


def test_validate_preflight_mode_accepts_dry_run_without_connector() -> None:
    issues = validate_preflight_mode(mode="dry-run", environment="live", connector_enabled=False)
    assert issues == []


def test_validate_preflight_mode_rejects_non_testnet_connector() -> None:
    issues = validate_preflight_mode(mode="testnet", environment="live", connector_enabled=True)
    assert "connector_environment_not_testnet_or_sandbox" in issues


def test_run_preflight_bundle_live_mode_rejected_before_runtime() -> None:
    with pytest.raises(ValueError) as exc:
        run_preflight_bundle(
            mode="live",
            environment="testnet",
            enable_live_trading=False,
            symbol="BTCUSDT",
            market_type="spot",
            connector_override=None,
        )
    assert "mode_live_blocked" in str(exc.value)
