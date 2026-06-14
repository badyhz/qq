"""Integration test: cancel and reconciliation governance draft."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_adapter_spec.cancel_reconciliation_governance import (
    get_cancel_items, get_recon_items, render_report
)


def test_cancel_items_present():
    items = get_cancel_items()
    assert len(items) >= 7


def test_recon_items_present():
    items = get_recon_items()
    assert len(items) >= 7


def test_governance_report_flags():
    cancel = get_cancel_items()
    recon = get_recon_items()
    report = render_report(cancel, recon)
    assert "cancel_gate_state=LOCKED" in report
    assert "reconciliation_gate_state=LOCKED" in report
    assert "testnet_cancel_allowed=false" in report
    assert "testnet_submit_allowed=false" in report


def test_governance_has_idempotency():
    cancel = get_cancel_items()
    recon = get_recon_items()
    report = render_report(cancel, recon)
    assert "idempotency" in report.lower()
