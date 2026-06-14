"""Integration test: exchange permission isolation plan."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_adapter_spec.exchange_permission_isolation import get_permissions, render_report


def test_permissions_present():
    perms = get_permissions()
    assert len(perms) >= 14


def test_permissions_no_withdraw():
    perms = get_permissions()
    no_withdraw = [p for p in perms if "withdraw" in p.title.lower()]
    assert len(no_withdraw) >= 1
    for p in no_withdraw:
        assert p.required is True


def test_permissions_report_flags():
    perms = get_permissions()
    report = render_report(perms)
    assert "EXCHANGE_PERMISSION_ISOLATION_PLAN_READY" in report
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in report


def test_permissions_testnet_only():
    perms = get_permissions()
    testnet = [p for p in perms if "testnet" in p.title.lower()]
    assert len(testnet) >= 1
