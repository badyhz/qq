"""Integration test: credential vault requirements."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_enablement.credential_vault_requirements import get_requirements


def test_credential_vault_requirements_count():
    reqs = get_requirements()
    assert len(reqs) >= 13


def test_credential_vault_requirements_categories():
    reqs = get_requirements()
    categories = {r.category for r in reqs}
    assert "storage" in categories
    assert "encryption" in categories
    assert "access" in categories
    assert "audit" in categories


def test_credential_vault_requirements_no_real_keys():
    reqs = get_requirements()
    for r in reqs:
        assert "real" not in r.description.lower() or "no real" in r.description.lower() or "real key" not in r.description.lower()


def test_credential_vault_requirements_statuses():
    reqs = get_requirements()
    for r in reqs:
        assert r.status in ("DOCUMENTED", "REQUIRED", "DESIGNED", "STUB_ONLY")
