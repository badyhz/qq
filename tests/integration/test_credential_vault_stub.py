"""Test credential vault stub."""
import pytest
from src.runtime_integrations.testnet_sandbox.credential_vault_stub import check_vault_stub, STUB_CREDENTIALS


def test_vault_stub_no_real_credentials():
    check = check_vault_stub()
    assert check.real_credentials_loaded is False


def test_vault_stub_no_env_read():
    check = check_vault_stub()
    assert check.env_secret_read is False


def test_vault_stub_mode():
    check = check_vault_stub()
    assert check.vault_mode == "STUB_ONLY"


def test_vault_stub_submit_blocked():
    check = check_vault_stub()
    assert check.submit_allowed is False


def test_vault_stub_all_redacted():
    check = check_vault_stub()
    assert check.all_redacted is True


def test_stub_credentials_count():
    assert len(STUB_CREDENTIALS) >= 3


def test_stub_credentials_redacted():
    for cred in STUB_CREDENTIALS:
        assert cred.value_redacted == "***STUB_REDACTED***"
        assert cred.vault_mode == "STUB_ONLY"
        assert cred.real_credentials_loaded is False
        assert cred.env_secret_read is False
        assert cred.submit_allowed is False
