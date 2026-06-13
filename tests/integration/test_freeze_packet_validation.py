"""Integration test: freeze packet validation."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_enablement.human_approval_freeze_packet import create_freeze_packet
from src.runtime_integrations.testnet_enablement.freeze_packet_validator import validate_freeze_packet


def test_freeze_packet_all_gates_locked():
    packet = create_freeze_packet()
    for gate in packet.frozen_gates:
        assert gate.state == "LOCKED"
        assert gate.submit_allowed is False


def test_freeze_packet_no_trading():
    packet = create_freeze_packet()
    assert packet.trading_enabled is False
    assert packet.submit_allowed is False


def test_freeze_packet_validator_passes():
    packet = create_freeze_packet()
    checks = validate_freeze_packet(packet)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)


def test_freeze_packet_required_approvals():
    packet = create_freeze_packet()
    assert len(packet.required_human_approvals) >= 3


def test_freeze_packet_forbidden_actions():
    packet = create_freeze_packet()
    assert len(packet.forbidden_actions) >= 5
