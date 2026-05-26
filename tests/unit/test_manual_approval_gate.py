"""Unit tests for ManualApprovalGate."""

from __future__ import annotations

import time

import pytest

from core.manual_approval_gate import (
    ApprovalConsumeResult,
    ApprovalRequest,
    ApprovalStatus,
    ManualApprovalGate,
)


@pytest.fixture
def gate() -> ManualApprovalGate:
    return ManualApprovalGate(default_ttl_seconds=3600)


@pytest.fixture
def short_gate() -> ManualApprovalGate:
    """Gate with 1-second TTL for expiry tests."""
    return ManualApprovalGate(default_ttl_seconds=1)


class TestRequestApproval:
    def test_returns_token(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("open_position", "binance_live")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_request_creates_pending(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("open_position", "binance_live")
        assert gate.check_status(token) == ApprovalStatus.PENDING

    def test_custom_ttl(self) -> None:
        g = ManualApprovalGate(default_ttl_seconds=60)
        token = g.request_approval("x", "y", ttl_seconds=10)
        req = g._requests[token]
        assert req.expires_at - req.created_at == pytest.approx(10, abs=0.1)


class TestApprove:
    def test_approve_sets_approved(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("sell", "adapter1")
        assert gate.approve(token) is True
        assert gate.check_status(token) == ApprovalStatus.APPROVED

    def test_approve_nonexistent(self, gate: ManualApprovalGate) -> None:
        assert gate.approve("bad-token") is False

    def test_approve_already_approved(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("sell", "adapter1")
        gate.approve(token)
        assert gate.approve(token) is False

    def test_approve_denied(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("sell", "adapter1")
        gate.deny(token)
        assert gate.approve(token) is False


class TestDeny:
    def test_deny_sets_denied(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("sell", "adapter1")
        assert gate.deny(token) is True
        assert gate.check_status(token) == ApprovalStatus.DENIED

    def test_deny_nonexistent(self, gate: ManualApprovalGate) -> None:
        assert gate.deny("bad-token") is False

    def test_deny_already_approved(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("sell", "adapter1")
        gate.approve(token)
        assert gate.deny(token) is False


class TestIsApproved:
    def test_true_for_valid_approval(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("buy", "live_adapter")
        gate.approve(token)
        assert gate.is_approved("buy", "live_adapter") is True

    def test_false_for_pending(self, gate: ManualApprovalGate) -> None:
        gate.request_approval("buy", "live_adapter")
        assert gate.is_approved("buy", "live_adapter") is False

    def test_false_for_no_requests(self, gate: ManualApprovalGate) -> None:
        assert gate.is_approved("unknown", "unknown") is False

    def test_false_for_expired(self, short_gate: ManualApprovalGate) -> None:
        token = short_gate.request_approval("buy", "adapter")
        short_gate.approve(token)
        time.sleep(1.1)
        assert short_gate.is_approved("buy", "adapter") is False

    def test_false_for_consumed(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("buy", "adapter")
        gate.approve(token)
        gate.consume(token)
        assert gate.is_approved("buy", "adapter") is False

    def test_false_for_denied(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("buy", "adapter")
        gate.deny(token)
        assert gate.is_approved("buy", "adapter") is False


class TestConsume:
    def test_consume_approved_succeeds(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("x", "a")
        gate.approve(token)
        result = gate.consume(token)
        assert result.success is True
        assert result.status == ApprovalStatus.CONSUMED
        assert result.detail == "consumed"

    def test_consume_already_consumed(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("x", "a")
        gate.approve(token)
        gate.consume(token)
        result = gate.consume(token)
        assert result.success is False
        assert result.status == ApprovalStatus.CONSUMED

    def test_consume_pending_fails(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("x", "a")
        result = gate.consume(token)
        assert result.success is False
        assert result.status == ApprovalStatus.PENDING

    def test_consume_nonexistent(self, gate: ManualApprovalGate) -> None:
        result = gate.consume("nope")
        assert result.success is False

    def test_single_use_enforcement(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("x", "a")
        gate.approve(token)
        r1 = gate.consume(token)
        r2 = gate.consume(token)
        assert r1.success is True
        assert r2.success is False
        assert gate.check_status(token) == ApprovalStatus.CONSUMED


class TestTTL:
    def test_expired_token_detected(self, short_gate: ManualApprovalGate) -> None:
        token = short_gate.request_approval("x", "a")
        short_gate.approve(token)
        time.sleep(1.1)
        assert short_gate.check_status(token) == ApprovalStatus.EXPIRED

    def test_is_approved_false_after_expiry(self, short_gate: ManualApprovalGate) -> None:
        token = short_gate.request_approval("x", "a")
        short_gate.approve(token)
        time.sleep(1.1)
        assert short_gate.is_approved("x", "a") is False


class TestRevoke:
    def test_revoke_pending(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("x", "a")
        assert gate.revoke(token) is True
        assert gate.check_status(token) == ApprovalStatus.REVOKED

    def test_revoke_approved(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("x", "a")
        gate.approve(token)
        assert gate.revoke(token) is True
        assert gate.check_status(token) == ApprovalStatus.REVOKED

    def test_revoke_nonexistent(self, gate: ManualApprovalGate) -> None:
        assert gate.revoke("bad") is False

    def test_revoke_denied_fails(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("x", "a")
        gate.deny(token)
        assert gate.revoke(token) is False

    def test_revoke_consumed_fails(self, gate: ManualApprovalGate) -> None:
        token = gate.request_approval("x", "a")
        gate.approve(token)
        gate.consume(token)
        assert gate.revoke(token) is False


class TestListPending:
    def test_lists_pending(self, gate: ManualApprovalGate) -> None:
        gate.request_approval("a1", "adapter1")
        gate.request_approval("a2", "adapter2")
        pending = gate.list_pending()
        assert len(pending) == 2
        actions = {p["action"] for p in pending}
        assert actions == {"a1", "a2"}

    def test_excludes_approved(self, gate: ManualApprovalGate) -> None:
        t1 = gate.request_approval("a1", "adapter1")
        gate.approve(t1)
        gate.request_approval("a2", "adapter2")
        pending = gate.list_pending()
        assert len(pending) == 1
        assert pending[0]["action"] == "a2"


class TestListApproved:
    def test_lists_approved(self, gate: ManualApprovalGate) -> None:
        t1 = gate.request_approval("a1", "adapter1")
        t2 = gate.request_approval("a2", "adapter2")
        gate.approve(t1)
        approved = gate.list_approved()
        assert len(approved) == 1
        assert approved[0]["token"] == t1

    def test_excludes_consumed(self, gate: ManualApprovalGate) -> None:
        t1 = gate.request_approval("a1", "adapter1")
        gate.approve(t1)
        gate.consume(t1)
        assert len(gate.list_approved()) == 0


class TestSummary:
    def test_summary_counts(self, gate: ManualApprovalGate) -> None:
        t1 = gate.request_approval("a", "b")
        t2 = gate.request_approval("c", "d")
        gate.approve(t1)
        gate.consume(t1)
        s = gate.summary()
        assert s["total"] == 2
        assert s["counts"]["consumed"] == 1
        assert s["counts"]["pending"] == 1
        assert s["default_ttl_seconds"] == 3600


class TestMultipleApprovals:
    def test_different_actions_independent(self, gate: ManualApprovalGate) -> None:
        t1 = gate.request_approval("buy", "adapter1")
        t2 = gate.request_approval("sell", "adapter1")
        gate.approve(t1)
        assert gate.is_approved("buy", "adapter1") is True
        assert gate.is_approved("sell", "adapter1") is False

    def test_different_adapters_independent(self, gate: ManualApprovalGate) -> None:
        t1 = gate.request_approval("buy", "adapter1")
        t2 = gate.request_approval("buy", "adapter2")
        gate.approve(t1)
        assert gate.is_approved("buy", "adapter1") is True
        assert gate.is_approved("buy", "adapter2") is False
