"""Integration test: network-off execution packet."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_release_gate.network_off_execution_packet import create_packet


def test_execution_packet_ready():
    packet = create_packet()
    assert "NETWORK_OFF_EXECUTION_PACKET_READY" in packet.network_off_verdict


def test_execution_steps_have_gates():
    packet = create_packet()
    gated = [s for s in packet.steps if s.network_required or s.submit_required or s.credential_required]
    assert len(gated) >= 2


def test_execution_steps_mostly_safe():
    packet = create_packet()
    safe = [s for s in packet.steps if s.would_execute and not s.network_required and not s.submit_required]
    assert len(safe) >= 3
