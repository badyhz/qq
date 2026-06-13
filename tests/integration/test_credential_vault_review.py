"""Test credential vault review."""
import pytest
from src.runtime_integrations.testnet_presubmit.credential_review import run_credential_review
from src.runtime_integrations.testnet_presubmit.credential_schema import get_schemas

def test_review_no_real_credentials():
    r = run_credential_review(2)
    assert r.real_credentials_loaded is False

def test_review_mode():
    r = run_credential_review(2)
    assert r.credential_mode == "REVIEW_STUB_ONLY"

def test_review_no_env_read():
    r = run_credential_review(2)
    assert r.env_secret_read is False

def test_review_no_file_read():
    r = run_credential_review(2)
    assert r.file_secret_read is False

def test_review_submit_blocked():
    r = run_credential_review(2)
    assert r.submit_allowed is False

def test_review_all_placeholder():
    r = run_credential_review(2)
    assert r.all_placeholder is True

def test_review_all_redacted():
    r = run_credential_review(2)
    assert r.all_redacted is True

def test_schemas_exist():
    schemas = get_schemas()
    assert len(schemas) >= 2

def test_schemas_have_required_fields():
    for s in get_schemas():
        assert s.exchange_name
        assert s.account_scope
        assert s.rotation_required is True
        assert s.redaction_required is True
        assert s.human_review_required is True
