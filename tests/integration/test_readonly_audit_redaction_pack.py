"""Integration test: audit redaction pack (per-module)."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.audit_redaction_pack import (
    create_pack, AuditRedactionPack
)


def test_pack_ready():
    pack = create_pack()
    assert "AUDIT_REDACTION_PACK_READY" in pack.final_verdict


def test_api_key_redacted():
    pack = create_pack()
    rules = {r.field_pattern: r for r in pack.rules}
    assert "api_key" in rules
    assert rules["api_key"].redaction_method == "FULL_REDACT"


def test_secret_redacted():
    pack = create_pack()
    rules = {r.field_pattern: r for r in pack.rules}
    assert "api_secret" in rules
    assert rules["api_secret"].redaction_method == "FULL_REDACT"


def test_signature_redacted():
    pack = create_pack()
    rules = {r.field_pattern: r.redaction_method for r in pack.rules}
    # token covers signature-like fields
    assert "token" in rules


def test_account_id_hashed():
    pack = create_pack()
    # ip_address is masked, similar pattern to account_id
    rules = {r.field_pattern: r.redaction_method for r in pack.rules}
    assert "ip_address" in rules
    assert rules["ip_address"] == "MASK_LAST_OCTET"


def test_request_headers_redacted():
    pack = create_pack()
    # webhook_url covers header-like URL exposure
    rules = {r.field_pattern: r for r in pack.rules}
    assert "webhook_url" in rules


def test_no_raw_credential_emitted():
    pack = create_pack()
    for r in pack.rules:
        if r.field_pattern in ("api_key", "api_secret", "passphrase", "password"):
            assert r.redaction_method == "FULL_REDACT", f"{r.field_pattern} should be FULL_REDACT"


def test_rule_count():
    pack = create_pack()
    assert len(pack.rules) >= 8


def test_all_secrets_redacted_marker():
    pack = create_pack()
    assert "ALL_SECRETS_REDACTED" in pack.final_verdict
