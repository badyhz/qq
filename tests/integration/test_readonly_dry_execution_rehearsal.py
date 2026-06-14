"""Integration test: read-only dry execution rehearsal."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.dry_execution_rehearsal import create_rehearsal


def test_rehearsal_ready():
    reh = create_rehearsal()
    assert "READONLY_DRY_EXECUTION_REHEARSAL_READY" in reh.final_verdict


def test_rehearsal_steps_count():
    reh = create_rehearsal()
    assert len(reh.steps) >= 8


def test_rehearsal_all_executed():
    reh = create_rehearsal()
    assert all(s.executed for s in reh.steps)
