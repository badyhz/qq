"""Integration test: gate blocker ledger."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_closeout.gate_blocker_ledger import (
    create_ledger, count_by_severity, count_by_category
)


def test_create_ledger():
    ledger = create_ledger()
    assert len(ledger.blockers) == 11
    assert ledger.ledger_id.startswith("GLD_")


def test_all_blockers_active():
    ledger = create_ledger()
    for b in ledger.blockers:
        assert b.current_status == "BLOCKED"
        assert b.final_decision == "BLOCKER_ACTIVE"


def test_count_by_severity():
    ledger = create_ledger()
    counts = count_by_severity(ledger)
    assert "CRITICAL" in counts
    assert "HIGH" in counts
    assert counts["CRITICAL"] >= 4
    assert counts["HIGH"] >= 4


def test_count_by_category():
    ledger = create_ledger()
    counts = count_by_category(ledger)
    assert "credential" in counts
    assert "permission" in counts
    assert "safety" in counts


def test_render_report():
    from src.runtime_integrations.testnet_mock_closeout.gate_blocker_ledger import render_report
    ledger = create_ledger()
    report = render_report(ledger)
    assert "GATE_BLOCKER_LEDGER_READY" in report
    assert "SUBMIT_UNLOCK_BLOCKED" in report
