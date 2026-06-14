"""Integration test: read-only discovery dry-run packet."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_discovery.discovery_dry_run_packet import create_packet


def test_create_packet():
    packet = create_packet()
    assert packet.packet_id.startswith("DRP_")
    assert len(packet.blocker_summary) >= 5


def test_final_recommendation():
    packet = create_packet()
    assert "DESIGN_READY" in packet.final_recommendation
    assert "REAL_NETWORK_STILL_BLOCKED" in packet.final_recommendation
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in packet.final_recommendation


def test_has_references():
    packet = create_packet()
    assert packet.discovery_design_ref != ""
    assert packet.credential_policy_ref != ""
    assert packet.capability_inventory_ref != ""


def test_render_report():
    from src.runtime_integrations.testnet_readonly_discovery.discovery_dry_run_packet import render_report
    packet = create_packet()
    report = render_report(packet)
    assert "READ_ONLY_DISCOVERY_DRY_RUN_PACKET_READY" in report
    assert "REAL_NETWORK_STILL_BLOCKED" in report
