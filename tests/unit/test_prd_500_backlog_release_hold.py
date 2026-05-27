"""Tests for T915 — 500 backlog release hold."""

import pytest

from core.prd_500_backlog_release_hold import (
    build_prd_500_backlog_release_hold,
    release_hold_to_dict,
    release_hold_to_markdown,
)


class TestPrd500BacklogReleaseHold:
    def test_hold_active(self):
        hold = build_prd_500_backlog_release_hold()
        assert hold.hold_active is True
        assert hold.final_verdict == "HOLD"

    def test_forbidden_actions_present(self):
        hold = build_prd_500_backlog_release_hold()
        must_forbid = [
            "live trading",
            "real order placement",
            "secret access",
            "exchange connection",
            "planner autonomous execution",
            "account state mutation",
        ]
        for action in must_forbid:
            assert action in hold.forbidden_actions

    def test_deterministic(self):
        a = build_prd_500_backlog_release_hold()
        b = build_prd_500_backlog_release_hold()
        assert a == b
        assert release_hold_to_dict(a) == release_hold_to_dict(b)
        assert release_hold_to_markdown(a) == release_hold_to_markdown(b)

    def test_no_live_authorization(self):
        hold = build_prd_500_backlog_release_hold()
        assert "no live trading authorization" in hold.hold_reasons
        assert "live trading" in hold.forbidden_actions
        assert "exchange connection" in hold.forbidden_actions
        assert hold.hold_active is True
