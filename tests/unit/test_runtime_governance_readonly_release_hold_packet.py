"""Tests for T855: Runtime governance read-only release hold packet."""

import pytest

from core.runtime_governance_readonly_release_hold_packet import (
    RuntimeGovernanceReadOnlyReleaseHoldPacket,
    build_readonly_release_hold_packet,
    readonly_release_hold_packet_to_dict,
    readonly_release_hold_packet_to_markdown,
)


class TestHoldPacketDefaults:
    """Test default hold packet values."""

    def test_hold_active_is_true(self):
        packet = build_readonly_release_hold_packet()
        assert packet.hold_active is True

    def test_final_verdict_is_hold(self):
        packet = build_readonly_release_hold_packet()
        assert packet.final_verdict == "HOLD"

    def test_forbidden_actions_present(self):
        packet = build_readonly_release_hold_packet()
        assert "live trading" in packet.forbidden_actions
        assert "order placement" in packet.forbidden_actions
        assert len(packet.forbidden_actions) >= 4


class TestDeterminism:
    """Test packet is deterministic."""

    def test_deterministic_construction(self):
        p1 = build_readonly_release_hold_packet()
        p2 = build_readonly_release_hold_packet()
        assert p1 == p2

    def test_to_dict_deterministic(self):
        p1 = build_readonly_release_hold_packet()
        p2 = build_readonly_release_hold_packet()
        assert readonly_release_hold_packet_to_dict(p1) == readonly_release_hold_packet_to_dict(p2)

    def test_to_markdown_deterministic(self):
        p1 = build_readonly_release_hold_packet()
        p2 = build_readonly_release_hold_packet()
        assert readonly_release_hold_packet_to_markdown(p1) == readonly_release_hold_packet_to_markdown(p2)


class TestToDict:
    """Test dict conversion."""

    def test_expected_keys(self):
        packet = build_readonly_release_hold_packet()
        d = readonly_release_hold_packet_to_dict(packet)
        expected_keys = {
            "hold_active",
            "hold_reasons",
            "allowed_actions",
            "forbidden_actions",
            "release_conditions",
            "final_verdict",
        }
        assert set(d.keys()) == expected_keys

    def test_dict_values_match(self):
        packet = build_readonly_release_hold_packet()
        d = readonly_release_hold_packet_to_dict(packet)
        assert d["hold_active"] is True
        assert d["final_verdict"] == "HOLD"


class TestToMarkdown:
    """Test markdown conversion."""

    def test_markdown_contains_hold(self):
        packet = build_readonly_release_hold_packet()
        md = readonly_release_hold_packet_to_markdown(packet)
        assert "HOLD" in md

    def test_markdown_contains_sections(self):
        packet = build_readonly_release_hold_packet()
        md = readonly_release_hold_packet_to_markdown(packet)
        assert "Hold Reasons" in md
        assert "Forbidden Actions" in md
        assert "Release Conditions" in md
