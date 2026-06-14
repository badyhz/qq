"""Integration test: vault stub contract."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_transport.vault_stub_contract import create_stub_state, render_report
from src.runtime_integrations.testnet_mock_transport.vault_stub_validator import validate_vault_stub


def test_stub_state():
    state = create_stub_state()
    assert state.mode == "STUB_ONLY"
    assert state.real_credentials_enabled is False
    assert state.env_secret_read is False
    assert state.submit_allowed is False


def test_stub_credentials_redacted():
    state = create_stub_state()
    for ref in state.credential_references:
        assert ref.redacted is True
        assert ref.placeholder is True
        assert "****" in ref.key_id


def test_report_flags():
    state = create_stub_state()
    report = render_report(state)
    assert "STUB_ONLY" in report
    assert "real_credentials_enabled=False" in report
    assert "env_secret_read=False" in report
    assert "submit_allowed=False" in report


def test_validator_passes():
    state = create_stub_state()
    report = render_report(state)
    checks = validate_vault_stub(report)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)


def test_no_raw_api_key():
    state = create_stub_state()
    report = render_report(state)
    checks = validate_vault_stub(report)
    no_raw = [c for c in checks if c.check_id == "no_raw_api_key"]
    assert len(no_raw) == 1
    assert no_raw[0].passed
