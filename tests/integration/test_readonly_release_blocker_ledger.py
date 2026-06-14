"""Integration test: read-only release blocker ledger."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_release_gate.release_blocker_ledger import create_ledger, count_active


def test_blocker_ledger_ready():
    ledger = create_ledger()
    assert "READONLY_DISCOVERY_RELEASE_BLOCKERS_READY" in ledger.final_verdict


def test_blocker_ledger_has_active_blockers():
    ledger = create_ledger()
    assert count_active(ledger) >= 3


def test_blocker_ledger_critical_blockers():
    ledger = create_ledger()
    critical = [b for b in ledger.blockers if b.severity == "CRITICAL"]
    assert len(critical) >= 3
