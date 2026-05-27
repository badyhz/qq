"""T842: Tests for runtime governance read-only manual review packet."""

import pytest

from core.runtime_governance_readonly_manual_review_packet import (
    RuntimeGovernanceReadOnlyManualReviewPacket,
    build_readonly_manual_review_packet,
    readonly_manual_review_packet_to_dict,
    readonly_manual_review_packet_to_markdown,
)


class TestBuildReadonlyManualReviewPacket:
    def test_default_packet_has_items(self):
        packet = build_readonly_manual_review_packet()
        assert len(packet.allowed_review_items) == 10
        assert len(packet.forbidden_actions) == 7
        assert len(packet.required_evidence) == 9
        assert len(packet.decision_options) == 2
        assert len(packet.notes) == 3

    def test_forbidden_actions_present(self):
        packet = build_readonly_manual_review_packet()
        assert "live trading" in packet.forbidden_actions
        assert "order placement" in packet.forbidden_actions
        assert "secret access" in packet.forbidden_actions
        assert "exchange connection" in packet.forbidden_actions

    def test_non_authorizations_present(self):
        packet = build_readonly_manual_review_packet()
        assert any("not authorize" in n.lower() for n in packet.notes)
        assert "APPROVE_READONLY_DESIGN_ONLY" in packet.decision_options

    def test_deterministic_output(self):
        p1 = build_readonly_manual_review_packet()
        p2 = build_readonly_manual_review_packet()
        assert readonly_manual_review_packet_to_dict(p1) == readonly_manual_review_packet_to_dict(p2)

    def test_frozen(self):
        packet = build_readonly_manual_review_packet()
        with pytest.raises(AttributeError):
            packet.allowed_review_items = []  # type: ignore[misc]


class TestToDict:
    def test_expected_keys(self):
        packet = build_readonly_manual_review_packet()
        d = readonly_manual_review_packet_to_dict(packet)
        assert set(d.keys()) == {
            "allowed_review_items",
            "forbidden_actions",
            "required_evidence",
            "decision_options",
            "notes",
        }
        assert isinstance(d["allowed_review_items"], list)

    def test_returns_copy(self):
        packet = build_readonly_manual_review_packet()
        d = readonly_manual_review_packet_to_dict(packet)
        d["allowed_review_items"].append("x")
        assert "x" not in packet.allowed_review_items


class TestToMarkdown:
    def test_contains_forbidden(self):
        packet = build_readonly_manual_review_packet()
        md = readonly_manual_review_packet_to_markdown(packet)
        assert "Forbidden Actions" in md
        assert "live trading" in md
        assert "order placement" in md

    def test_contains_decision_options(self):
        packet = build_readonly_manual_review_packet()
        md = readonly_manual_review_packet_to_markdown(packet)
        assert "APPROVE_READONLY_DESIGN_ONLY" in md
        assert "REQUEST_CHANGES" in md

    def test_contains_notes(self):
        packet = build_readonly_manual_review_packet()
        md = readonly_manual_review_packet_to_markdown(packet)
        assert "Does not authorize live trading" in md
        assert "Does not authorize order placement" in md
