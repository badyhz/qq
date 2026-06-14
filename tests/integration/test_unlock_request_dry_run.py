"""Integration test: unlock request dry-run."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_transport.unlock_request_dry_run import (
    create_unlock_request, render_report
)


def test_submit_unlock_denied():
    req = create_unlock_request("submit")
    assert req.decision == "DENY"
    assert req.approved is False
    assert len(req.blockers) >= 5


def test_cancel_unlock_denied():
    req = create_unlock_request("cancel")
    assert req.decision == "DENY"
    assert req.approved is False
    assert len(req.blockers) >= 3


def test_recon_unlock_denied():
    req = create_unlock_request("reconciliation")
    assert req.decision == "DENY"
    assert req.approved is False
    assert len(req.blockers) >= 3


def test_report_flags():
    report = render_report()
    assert "DRY_RUN_ONLY" in report
    assert "submit_gate_state=LOCKED" in report
    assert "cancel_gate_state=LOCKED" in report
    assert "reconciliation_gate_state=LOCKED" in report
    assert "approved=false" in report
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in report
