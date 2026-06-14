"""Integration test: operator handoff packet (per-module)."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_governance_freeze.operator_handoff_packet import (
    create_packet, OperatorHandoffPacket
)


def test_packet_ready():
    packet = create_packet()
    assert "READONLY_OPERATOR_HANDOFF_PACKET_READY" in packet.final_verdict


def test_includes_completed_stages():
    packet = create_packet()
    milestones = [i for i in packet.items if i.category == "MILESTONE"]
    assert len(milestones) >= 8
    assert all(m.status == "DONE" for m in milestones)


def test_includes_remaining_blockers():
    packet = create_packet()
    constraints = [i for i in packet.items if i.category == "CONSTRAINT"]
    assert len(constraints) >= 3


def test_includes_rollback_reference():
    packet = create_packet()
    descriptions = [i.description.lower() for i in packet.items]
    assert any("real network" in d or "blocked" in d for d in descriptions)


def test_includes_kill_switch_reference():
    packet = create_packet()
    descriptions = [i.description.lower() for i in packet.items]
    assert any("credential" in d or "blocked" in d for d in descriptions)


def test_next_human_decision_required():
    packet = create_packet()
    next_steps = [i for i in packet.items if i.category == "NEXT_STEP"]
    assert len(next_steps) >= 1
    assert any("human" in i.description.lower() for i in next_steps)


def test_item_count():
    packet = create_packet()
    assert len(packet.items) >= 12
