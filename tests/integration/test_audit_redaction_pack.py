"""Integration test: audit redaction pack."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.audit_redaction_pack import create_pack


def test_redaction_ready():
    pack = create_pack()
    assert "AUDIT_REDACTION_PACK_READY" in pack.final_verdict


def test_redaction_rules_count():
    pack = create_pack()
    assert len(pack.rules) >= 8


def test_secrets_fully_redacted():
    pack = create_pack()
    secret_rules = [r for r in pack.rules if r.field_pattern in ("api_key", "api_secret", "passphrase", "password")]
    assert all(r.redaction_method == "FULL_REDACT" for r in secret_rules)
