"""Integration test: read-only discovery release gate."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_release_gate.release_gate import create_packet


def test_release_gate_ready():
    packet = create_packet()
    assert "READONLY_DISCOVERY_RELEASE_GATE_READY" in packet.final_decision


def test_release_gate_no_network():
    packet = create_packet()
    assert "REAL_NETWORK_NOT_ALLOWED" in packet.final_decision


def test_release_gate_no_submit():
    packet = create_packet()
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in packet.final_decision


def test_release_gate_criteria_count():
    packet = create_packet()
    assert len(packet.criteria) >= 8
