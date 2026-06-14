"""Integration test: human approval packet v3."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_replay.human_approval_packet_v3 import create_packet, render_report


def test_packet_created():
    packet = create_packet("BUNDLE_TEST_001")
    assert packet.packet_id.startswith("APPROVAL_V3_")
    assert packet.decision == "APPROVAL_PACKET_GENERATED"


def test_packet_submit_blocked():
    packet = create_packet("BUNDLE_TEST_001")
    assert packet.submit_unlock_blocked is True
    assert packet.human_approval_required is True
    assert packet.operator_ack is False


def test_packet_checklists():
    packet = create_packet("BUNDLE_TEST_001")
    assert len(packet.checklists) >= 10


def test_packet_report_flags():
    packet = create_packet("BUNDLE_TEST_001")
    report = render_report(packet)
    assert "SUBMIT_UNLOCK_BLOCKED" in report
    assert "HUMAN_APPROVAL_REQUIRED" in report
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in report
    assert "HUMAN_APPROVAL_PACKET_V3_READY" in report
