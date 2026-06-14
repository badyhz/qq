"""Integration test: read-only final governance freeze."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_governance_freeze.final_governance_freeze import create_freeze


def test_freeze_ready():
    freeze = create_freeze()
    assert "READONLY_FINAL_GOVERNANCE_FREEZE_READY" in freeze.final_verdict


def test_all_decisions_frozen():
    freeze = create_freeze()
    assert all(d.status == "FROZEN" for d in freeze.decisions)


def test_decision_count():
    freeze = create_freeze()
    assert len(freeze.decisions) >= 8
