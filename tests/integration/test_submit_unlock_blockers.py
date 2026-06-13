"""Integration test: submit unlock blockers."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_enablement.submit_unlock_blocker_matrix import get_blockers


def test_submit_blockers_count():
    blockers = get_blockers()
    assert len(blockers) >= 10


def test_submit_blockers_has_blocking():
    blockers = get_blockers()
    blocking = [b for b in blockers if b.status == "BLOCKING"]
    assert len(blocking) >= 4


def test_submit_blockers_gate_remains_locked():
    blockers = get_blockers()
    blocking = [b for b in blockers if b.status == "BLOCKING"]
    assert len(blocking) > 0, "Gate must remain locked with BLOCKING items"


def test_submit_blockers_statuses():
    blockers = get_blockers()
    valid_statuses = ("BLOCKING", "REQUIRES_HUMAN_APPROVAL", "REQUIRES_FIELD_TEST", "REQUIRES_SECURITY_REVIEW", "DESIGNED_ONLY")
    for b in blockers:
        assert b.status in valid_statuses
