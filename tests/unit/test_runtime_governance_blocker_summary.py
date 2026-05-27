"""Tests for runtime governance blocker summary.

Deterministic. No I/O. No network. No random. No timestamps.
"""

import pytest

from core.runtime_governance_sample_factory import (
    build_runtime_governance_sample_preflight_packet,
)
from core.runtime_governance_blocker_summary import (
    RuntimeGovernanceBlockerSummary,
    summarize_runtime_governance_blockers,
    blocker_summary_to_dict,
    blocker_summary_to_markdown,
)


class TestSummarizeRuntimeGovernanceBlockers:
    """summarize_runtime_governance_blockers tests."""

    def test_valid_packet_zero_blockers_proceed(self):
        """Valid packet -> 0 blockers, PROCEED."""
        packet = build_runtime_governance_sample_preflight_packet("pass")
        summary = summarize_runtime_governance_blockers(packet)

        assert summary.total_blockers == 0
        assert summary.critical_blockers == 0
        assert summary.policy_blockers == 0
        assert summary.by_category == {}
        assert summary.by_source == {}
        assert summary.recommended_action == "PROCEED"

    def test_blocked_packet_critical_blockers_block(self):
        """Blocked packet -> critical/policy blockers, BLOCK."""
        packet = build_runtime_governance_sample_preflight_packet("blocked")
        summary = summarize_runtime_governance_blockers(packet)

        assert summary.total_blockers > 0
        assert summary.critical_blockers > 0
        assert summary.policy_blockers > 0
        assert summary.recommended_action == "BLOCK"

    def test_fail_packet_non_critical_review(self):
        """Fail packet with non-critical failures -> REVIEW."""
        packet = build_runtime_governance_sample_preflight_packet("fail")
        summary = summarize_runtime_governance_blockers(packet)

        assert summary.total_blockers > 0
        assert summary.critical_blockers == 0
        assert summary.policy_blockers == 0
        assert summary.recommended_action == "REVIEW"

    def test_counts_deterministic(self):
        """Building summary twice yields identical counts."""
        packet = build_runtime_governance_sample_preflight_packet("blocked")
        s1 = summarize_runtime_governance_blockers(packet)
        s2 = summarize_runtime_governance_blockers(packet)

        assert s1.total_blockers == s2.total_blockers
        assert s1.critical_blockers == s2.critical_blockers
        assert s1.policy_blockers == s2.policy_blockers
        assert s1.by_category == s2.by_category
        assert s1.by_source == s2.by_source
        assert s1.recommended_action == s2.recommended_action


class TestBlockerSummarySerialization:
    """blocker_summary_to_dict and blocker_summary_to_markdown tests."""

    def test_to_dict_pass(self):
        """Dict serialization for pass case."""
        packet = build_runtime_governance_sample_preflight_packet("pass")
        summary = summarize_runtime_governance_blockers(packet)
        d = blocker_summary_to_dict(summary)

        assert d["total_blockers"] == 0
        assert d["critical_blockers"] == 0
        assert d["policy_blockers"] == 0
        assert d["by_category"] == {}
        assert d["by_source"] == {}
        assert d["recommended_action"] == "PROCEED"

    def test_to_dict_blocked(self):
        """Dict serialization for blocked case."""
        packet = build_runtime_governance_sample_preflight_packet("blocked")
        summary = summarize_runtime_governance_blockers(packet)
        d = blocker_summary_to_dict(summary)

        assert d["total_blockers"] > 0
        assert d["recommended_action"] == "BLOCK"
        assert "policy_block" in d["by_category"]

    def test_markdown_deterministic(self):
        """Markdown output is deterministic across calls."""
        packet = build_runtime_governance_sample_preflight_packet("blocked")
        summary = summarize_runtime_governance_blockers(packet)
        md1 = blocker_summary_to_markdown(summary)
        md2 = blocker_summary_to_markdown(summary)

        assert md1 == md2

    def test_markdown_contains_action(self):
        """Markdown contains recommended action."""
        packet = build_runtime_governance_sample_preflight_packet("pass")
        summary = summarize_runtime_governance_blockers(packet)
        md = blocker_summary_to_markdown(summary)

        assert "PROCEED" in md

    def test_markdown_contains_category_breakdown(self):
        """Markdown contains category breakdown for blocked case."""
        packet = build_runtime_governance_sample_preflight_packet("blocked")
        summary = summarize_runtime_governance_blockers(packet)
        md = blocker_summary_to_markdown(summary)

        assert "policy_block" in md
        assert "BLOCK" in md


class TestRuntimeGovernanceBlockerSummaryDataclass:
    """RuntimeGovernanceBlockerSummary dataclass tests."""

    def test_frozen(self):
        """Summary is frozen/immutable."""
        packet = build_runtime_governance_sample_preflight_packet("pass")
        summary = summarize_runtime_governance_blockers(packet)

        with pytest.raises(AttributeError):
            summary.total_blockers = 99  # type: ignore[misc]

    def test_invalid_contract_packet(self):
        """Invalid contract mode still produces REVIEW summary."""
        packet = build_runtime_governance_sample_preflight_packet("invalid_contract")
        summary = summarize_runtime_governance_blockers(packet)

        assert summary.total_blockers > 0
        assert summary.critical_blockers == 0
        assert summary.policy_blockers == 0
        assert summary.recommended_action == "REVIEW"
