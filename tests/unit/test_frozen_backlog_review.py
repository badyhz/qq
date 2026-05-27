"""T1345 - Tests for frozen backlog review models."""
from __future__ import annotations

import pytest

from core.frozen_backlog_item_kind import FrozenBacklogItemKind, ALL_KINDS, build_kind
from core.frozen_backlog_review_state import FrozenBacklogReviewState, ALL_STATES, build_state
from core.frozen_backlog_denial_reason import FrozenBacklogDenialReason, build_denial_reason
from core.frozen_backlog_review_verdict import (
    FrozenBacklogReviewVerdict,
    VALID_VERDICTS,
    build_verdict,
)
from core.frozen_backlog_review import FrozenBacklogReview, build_review
from core.frozen_backlog_human_approval import build_human_approval


class TestFrozenBacklogItemKind:
    def test_create_valid_kind(self):
        kind = FrozenBacklogItemKind(kind="HIGH_RISK_FROZEN")
        assert kind.kind == "HIGH_RISK_FROZEN"

    def test_immutable(self):
        kind = FrozenBacklogItemKind(kind="MEDIUM_OPERATIONAL")
        with pytest.raises(AttributeError):
            kind.kind = "OTHER"  # type: ignore[misc]

    def test_invalid_kind_raises(self):
        with pytest.raises(ValueError, match="Invalid kind"):
            FrozenBacklogItemKind(kind="BOGUS")

    def test_all_kinds_contains_expected(self):
        assert "HIGH_RISK_FROZEN" in ALL_KINDS
        assert "MEDIUM_OPERATIONAL" in ALL_KINDS
        assert "MEDIUM_VERIFICATION" in ALL_KINDS

    def test_build_kind_factory(self):
        k = build_kind("MEDIUM_VERIFICATION")
        assert k.kind == "MEDIUM_VERIFICATION"


class TestFrozenBacklogReviewState:
    def test_create_valid_state(self):
        state = FrozenBacklogReviewState(state="PENDING")
        assert state.state == "PENDING"

    def test_immutable(self):
        state = FrozenBacklogReviewState(state="IN_REVIEW")
        with pytest.raises(AttributeError):
            state.state = "DENIED"  # type: ignore[misc]

    def test_invalid_state_raises(self):
        with pytest.raises(ValueError, match="Invalid state"):
            FrozenBacklogReviewState(state="INVALID")

    def test_all_states_contains_expected(self):
        for s in ("PENDING", "IN_REVIEW", "APPROVED", "DENIED", "ESCALATED"):
            assert s in ALL_STATES


class TestFrozenBacklogReviewVerdict:
    def test_build_valid_verdict(self):
        v = build_verdict(verdict="HOLD", notes="waiting")
        assert v.verdict == "HOLD"
        assert v.notes == "waiting"

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValueError, match="Invalid verdict"):
            build_verdict(verdict="BOGUS")

    def test_all_valid_verdicts(self):
        for v in VALID_VERDICTS:
            verdict = build_verdict(verdict=v)
            assert verdict.verdict == v

    def test_verdict_with_denial_reasons(self):
        reason = build_denial_reason("r1", "safety", "missing proof")
        v = build_verdict(verdict="DENIED", denial_reasons=(reason,))
        assert len(v.denial_reasons) == 1
        assert v.denial_reasons[0].reason_id == "r1"

    def test_verdict_with_approvals(self):
        approval = build_human_approval("a1", "reviewer1", "2026-01-01", "APPROVED")
        v = build_verdict(verdict="APPROVED", approvals=(approval,))
        assert len(v.approvals) == 1


class TestFrozenBacklogReview:
    def test_build_review_default_state(self):
        r = build_review(review_id="R1")
        assert r.review_id == "R1"
        assert r.review_state.state == "PENDING"
        assert r.verdict is None

    def test_review_immutable(self):
        r = build_review(review_id="R2")
        with pytest.raises(AttributeError):
            r.review_id = "X"  # type: ignore[misc]
