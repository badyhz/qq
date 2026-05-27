"""Tests for runtime governance regression packet.

Sync only. No async. No I/O. No network. No random.
"""

from __future__ import annotations

import pytest

from core.runtime_governance_regression_packet import (
    RuntimeGovernanceRegressionPacket,
    build_runtime_governance_regression_packet,
    runtime_regression_packet_to_dict,
    runtime_regression_packet_to_markdown,
)


# ── tests ─────────────────────────────────────────────────────────────


class TestDefaultPacketPass:
    def test_default_packet_verdict_pass(self):
        pkt = build_runtime_governance_regression_packet()

        assert pkt.final_verdict == "PASS"
        assert pkt.scenario_count == pkt.scenario_pass_count
        assert pkt.scenario_fail_count == 0
        assert pkt.manifest_summary["verdict"] == "PASS"
        assert pkt.scenario_count > 0
        assert "total" in pkt.invariant_summary


class TestDictDeterministic:
    def test_dict_same_on_repeat(self):
        pkt = build_runtime_governance_regression_packet()
        d1 = runtime_regression_packet_to_dict(pkt)
        d2 = runtime_regression_packet_to_dict(pkt)

        assert d1 == d2

    def test_dict_keys(self):
        pkt = build_runtime_governance_regression_packet()
        d = runtime_regression_packet_to_dict(pkt)

        expected_keys = {
            "title",
            "scenario_count",
            "scenario_pass_count",
            "scenario_fail_count",
            "invariant_summary",
            "manifest_summary",
            "final_verdict",
            "notes",
        }
        assert expected_keys == set(d.keys())


class TestMarkdownDeterministic:
    def test_markdown_same_on_repeat(self):
        pkt = build_runtime_governance_regression_packet()
        md1 = runtime_regression_packet_to_markdown(pkt)
        md2 = runtime_regression_packet_to_markdown(pkt)

        assert md1 == md2


class TestMarkdownContainsVerdict:
    def test_markdown_contains_final_verdict(self):
        pkt = build_runtime_governance_regression_packet()
        md = runtime_regression_packet_to_markdown(pkt)

        assert "**Final Verdict:** PASS" in md


class TestMarkdownContainsSections:
    def test_markdown_has_all_sections(self):
        pkt = build_runtime_governance_regression_packet()
        md = runtime_regression_packet_to_markdown(pkt)

        assert "## Scenario Evaluations" in md
        assert "## Invariant Summary" in md
        assert "## Manifest Summary" in md


class TestNotesPassthrough:
    def test_notes_collected(self):
        pkt = build_runtime_governance_regression_packet(
            notes=["note-x", "note-y"]
        )

        assert "note-x" in pkt.notes
        assert "note-y" in pkt.notes

    def test_markdown_contains_notes(self):
        pkt = build_runtime_governance_regression_packet(
            notes=["test-note"]
        )
        md = runtime_regression_packet_to_markdown(pkt)

        assert "## Notes" in md
        assert "- test-note" in md


class TestCustomTitle:
    def test_custom_title(self):
        pkt = build_runtime_governance_regression_packet(title="Custom Title")

        assert pkt.title == "Custom Title"

        md = runtime_regression_packet_to_markdown(pkt)
        assert "# Custom Title" in md
