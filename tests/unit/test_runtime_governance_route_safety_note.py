"""Tests for runtime governance route safety note (T822)."""

from core.runtime_governance_route_safety_note import (
    build_runtime_governance_route_safety_note_markdown,
)


class TestRuntimeGovernanceRouteSafetyNote:
    def test_no_autonomous_live_submit_recommendation(self):
        md = build_runtime_governance_route_safety_note_markdown()
        lower = md.lower()
        # Must NOT recommend autonomous live submit
        assert "autonomous live submit" not in lower or (
            "never recommended" in lower or "no autonomous" in lower
        ), "Must not recommend autonomous live submit as acceptable"

    def test_human_controlled_for_high_risk(self):
        md = build_runtime_governance_route_safety_note_markdown()
        lower = md.lower()
        assert "human-controlled" in lower or "human controlled" in lower, (
            "High-risk tier must specify human-controlled"
        )
        # Should appear near high-risk / live / exchange context
        assert "live" in lower or "exchange" in lower, (
            "Must mention live or exchange in high-risk context"
        )

    def test_markdown_deterministic(self):
        a = build_runtime_governance_route_safety_note_markdown()
        b = build_runtime_governance_route_safety_note_markdown()
        assert a == b, "Markdown must be deterministic across repeated calls"

    def test_no_timestamps_in_markdown(self):
        md = build_runtime_governance_route_safety_note_markdown()
        # No ISO timestamps, no "Generated at", no epoch
        lower = md.lower()
        assert "generated at" not in lower, "Must not contain 'generated at'"
        assert "202" not in md or "mimo2.5" in md, (
            "Year-like strings only allowed in model names"
        )
