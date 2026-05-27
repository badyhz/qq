"""Tests for runtime governance manual scope packet.

Deterministic. No I/O. No network. No random.
"""

from __future__ import annotations

import pytest

from core.runtime_governance_manual_scope_packet import (
    RuntimeGovernanceManualScopePacket,
    build_runtime_governance_manual_scope_packet,
    manual_scope_packet_to_dict,
    manual_scope_packet_to_markdown,
)


@pytest.fixture
def default_packet() -> RuntimeGovernanceManualScopePacket:
    return build_runtime_governance_manual_scope_packet()


# ── forbidden list ──────────────────────────────────────────────────────


class TestForbiddenList:
    def test_contains_live_trading(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert "live trading" in default_packet.forbidden_next_steps

    def test_contains_real_submit(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert "real submit" in default_packet.forbidden_next_steps

    def test_contains_secret_access(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert "secret access" in default_packet.forbidden_next_steps

    def test_contains_planner_autonomous_integration(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert "planner autonomous integration" in default_packet.forbidden_next_steps

    def test_contains_account_state_mutation(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert "account state mutation" in default_packet.forbidden_next_steps


# ── allowed list ────────────────────────────────────────────────────────


class TestAllowedList:
    def test_limited_to_review_scope_dry_run(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        expected = {
            "review preflight results",
            "review regression packet",
            "scope future tasks",
            "dry-run design review",
            "frozen boundary review",
        }
        assert set(default_packet.allowed_next_steps) == expected

    def test_no_overlap_with_forbidden(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        overlap = set(default_packet.allowed_next_steps) & set(default_packet.forbidden_next_steps)
        assert overlap == set()


# ── required reviews ────────────────────────────────────────────────────


class TestRequiredReviews:
    def test_non_empty(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert len(default_packet.required_reviews) > 0

    def test_contains_preflight(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert "pre-flight packet review" in default_packet.required_reviews

    def test_contains_regression(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert "regression packet review" in default_packet.required_reviews

    def test_contains_no_submit_evidence(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert "no-submit evidence review" in default_packet.required_reviews

    def test_contains_phase_control(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert "phase control report review" in default_packet.required_reviews


# ── final scope ─────────────────────────────────────────────────────────


class TestFinalScope:
    def test_default_value(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert default_packet.final_scope == "manual review and read-only analysis only"


# ── dict determinism ────────────────────────────────────────────────────


class TestDictDeterministic:
    def test_same_packet_same_dict(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        d1 = manual_scope_packet_to_dict(default_packet)
        d2 = manual_scope_packet_to_dict(default_packet)
        assert d1 == d2

    def test_dict_keys(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        d = manual_scope_packet_to_dict(default_packet)
        assert set(d.keys()) == {
            "allowed_next_steps",
            "forbidden_next_steps",
            "required_reviews",
            "final_scope",
            "notes",
        }

    def test_lists_are_copies(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        d = manual_scope_packet_to_dict(default_packet)
        assert d["allowed_next_steps"] is not default_packet.allowed_next_steps


# ── markdown determinism ────────────────────────────────────────────────


class TestMarkdownDeterministic:
    def test_same_packet_same_markdown(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        m1 = manual_scope_packet_to_markdown(default_packet)
        m2 = manual_scope_packet_to_markdown(default_packet)
        assert m1 == m2

    def test_contains_header(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        md = manual_scope_packet_to_markdown(default_packet)
        assert md.startswith("# Manual Scope Packet")

    def test_contains_all_sections(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        md = manual_scope_packet_to_markdown(default_packet)
        for section in ["## Allowed Next Steps", "## Forbidden Next Steps", "## Required Reviews", "## Notes"]:
            assert section in md


# ── frozen ──────────────────────────────────────────────────────────────


class TestFrozen:
    def test_dataclass_is_frozen(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        with pytest.raises(AttributeError):
            default_packet.final_scope = "mutated"  # type: ignore[misc]


# ── custom inputs ───────────────────────────────────────────────────────


class TestCustomInputs:
    def test_custom_allowed(self) -> None:
        pkt = build_runtime_governance_manual_scope_packet(allowed_next_steps=["foo"])
        assert pkt.allowed_next_steps == ["foo"]

    def test_custom_forbidden(self) -> None:
        pkt = build_runtime_governance_manual_scope_packet(forbidden_next_steps=["bar"])
        assert pkt.forbidden_next_steps == ["bar"]

    def test_default_notes_non_empty(self, default_packet: RuntimeGovernanceManualScopePacket) -> None:
        assert len(default_packet.notes) > 0
