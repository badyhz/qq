"""Test no-submit sandbox smoke."""
import pytest
from src.runtime_integrations.testnet_sandbox.no_submit_sandbox_smoke import run_smoke


def test_smoke_empty_signals():
    result = run_smoke([])
    assert result.no_real_submit is True
    assert result.no_testnet_submit is True
    assert result.no_network_calls is True
    assert result.no_key_reads is True
    assert result.overall == "NO_SUBMIT_SANDBOX_SMOKE_PASS"


def test_smoke_with_signals():
    signals = [
        {"signal_id": "SIG_001", "symbol": "BTCUSDT", "side": "BUY"},
        {"signal_id": "SIG_002", "symbol": "ETHUSDT", "side": "SELL"},
    ]
    result = run_smoke(signals)
    assert result.no_real_submit is True
    assert result.overall == "NO_SUBMIT_SANDBOX_SMOKE_PASS"


def test_smoke_steps_all_pass_or_blocked():
    result = run_smoke([])
    for s in result.steps:
        assert s.status in ("PASS", "BLOCKED", "SIMULATED")
