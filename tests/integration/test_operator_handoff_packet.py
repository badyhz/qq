"""Integration test: operator handoff packet."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_governance_freeze.operator_handoff_packet import create_packet


def test_handoff_ready():
    packet = create_packet()
    assert "READONLY_OPERATOR_HANDOFF_PACKET_READY" in packet.final_verdict


def test_all_milestones_done():
    packet = create_packet()
    milestones = [i for i in packet.items if i.category == "MILESTONE"]
    assert all(m.status == "DONE" for m in milestones)


def test_has_pending_next_step():
    packet = create_packet()
    pending = [i for i in packet.items if i.status == "PENDING"]
    assert len(pending) >= 1
