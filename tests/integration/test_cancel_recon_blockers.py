"""Integration test: cancel and reconciliation blockers."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_enablement.cancel_reconciliation_unlock_blockers import (
    get_cancel_blockers, get_recon_blockers
)


def test_cancel_blockers_count():
    blockers = get_cancel_blockers()
    assert len(blockers) >= 6


def test_recon_blockers_count():
    blockers = get_recon_blockers()
    assert len(blockers) >= 6


def test_cancel_blockers_has_blocking():
    blockers = get_cancel_blockers()
    blocking = [b for b in blockers if b.status == "BLOCKING"]
    assert len(blocking) >= 2


def test_recon_blockers_has_blocking():
    blockers = get_recon_blockers()
    blocking = [b for b in blockers if b.status == "BLOCKING"]
    assert len(blocking) >= 2


def test_cancel_gate_remains_locked():
    blockers = get_cancel_blockers()
    blocking = [b for b in blockers if b.status == "BLOCKING"]
    assert len(blocking) > 0, "Cancel gate must remain locked"


def test_recon_gate_remains_locked():
    blockers = get_recon_blockers()
    blocking = [b for b in blockers if b.status == "BLOCKING"]
    assert len(blocking) > 0, "Reconciliation gate must remain locked"
