"""Integration test: read-only discovery approval packet."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_preapproval.approval_packet import create_packet


def test_create_packet():
    packet = create_packet()
    assert packet.packet_id.startswith("APR_")
    assert len(packet.blockers) >= 5


def test_allowed_scope():
    packet = create_packet()
    assert "READ_ONLY_DISCOVERY_REVIEW" in packet.allowed_scope
    assert "NO_NETWORK_PREFLIGHT_REVIEW" in packet.allowed_scope


def test_prohibited_scope():
    packet = create_packet()
    assert "REAL_NETWORK_CALL" in packet.prohibited_scope
    assert "TESTNET_SUBMIT" in packet.prohibited_scope
    assert "REAL_TRADING" in packet.prohibited_scope


def test_declarations():
    packet = create_packet()
    assert "NO_REAL_NETWORK" in packet.no_network_declaration
    assert "NO_SUBMIT" in packet.no_submit_declaration


def test_final_decision():
    packet = create_packet()
    assert "APPROVAL_PACKET_READY" in packet.final_decision
    assert "HUMAN_APPROVAL_REQUIRED" in packet.final_decision
    assert "REAL_NETWORK_NOT_ALLOWED" in packet.final_decision
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in packet.final_decision


def test_render_report():
    from src.runtime_integrations.testnet_readonly_preapproval.approval_packet import render_report
    packet = create_packet()
    report = render_report(packet)
    assert "READONLY_DISCOVERY_APPROVAL_PACKET_READY" in report
    assert "HUMAN_APPROVAL_REQUIRED" in report
