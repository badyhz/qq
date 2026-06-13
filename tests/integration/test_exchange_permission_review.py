"""Integration test: exchange permission review."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_enablement.exchange_permission_review import get_permissions


def test_exchange_permissions_count():
    perms = get_permissions()
    assert len(perms) >= 11


def test_exchange_permissions_no_withdraw():
    perms = get_permissions()
    no_withdraw = [p for p in perms if "withdraw" in p.description.lower()]
    assert len(no_withdraw) >= 1
    for p in no_withdraw:
        assert p.required is True


def test_exchange_permissions_statuses():
    perms = get_permissions()
    for p in perms:
        assert p.status in ("NOT_CONFIGURED", "DESIGNED_ONLY", "BLOCKED")


def test_exchange_permissions_no_submit_allowed():
    perms = get_permissions()
    for p in perms:
        assert p.status != "SUBMIT_ALLOWED"
