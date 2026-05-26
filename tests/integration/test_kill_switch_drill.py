"""Kill Switch Drill — integration tests for failure/revocation scenarios.

NO network. NO real adapter calls. Pure in-process component interaction.
"""

from __future__ import annotations

import time

import pytest

from core.adapter_preflight import AdapterPreflightValidator, PreflightStatus
from core.live_capability_registry import LiveCapability, LiveCapabilityRegistry
from core.manual_approval_gate import ManualApprovalGate, ApprovalStatus
from core.real_adapter_policy import RealAdapterPolicy
from core.workflow_circuit_breaker import CircuitBreaker, CircuitState


ADAPTER_ID = "test-adapter"
ACTION = "trade.btcusdt"


class TestKillSwitchBeforeCall:
    """Activate kill switch → validate_request blocked."""

    def test_global_kill_switch_blocks_adapter_request(self):
        policy = RealAdapterPolicy()
        policy.register(ADAPTER_ID, {"endpoint": "https://sandbox.example.com"})
        policy.add_to_allowlist(ADAPTER_ID)

        # Before kill switch: allowed
        result = policy.validate_request(ADAPTER_ID, {})
        assert result.allowed is True

        # Activate global kill switch
        policy.activate_kill_switch()

        # After kill switch: blocked
        result = policy.validate_request(ADAPTER_ID, {})
        assert result.allowed is False
        assert any(v.rule == "kill_switch_global" for v in result.violations)
        assert policy.is_kill_switch_active(ADAPTER_ID) is True

    def test_adapter_kill_switch_blocks_specific_adapter(self):
        policy = RealAdapterPolicy()
        policy.register(ADAPTER_ID, {"endpoint": "https://sandbox.example.com"})
        policy.add_to_allowlist(ADAPTER_ID)

        # Kill only this adapter
        policy.activate_kill_switch(adapter_id=ADAPTER_ID)

        result = policy.validate_request(ADAPTER_ID, {})
        assert result.allowed is False
        assert any(v.rule == "kill_switch_adapter" for v in result.violations)

        # Global still off
        assert policy._kill_switch_active is False


class TestKillSwitchDuringPreflight:
    """Preflight passes, kill switch activates, preflight fails."""

    def test_preflight_fails_after_kill_switch(self):
        policy = RealAdapterPolicy()
        policy.register(ADAPTER_ID, {"endpoint": "https://sandbox.example.com"})
        policy.add_to_allowlist(ADAPTER_ID)

        # Approve so approval check passes
        gate = ManualApprovalGate()
        token = gate.request_approval(ACTION, ADAPTER_ID)
        gate.approve(token)

        # Capability allowed
        registry = LiveCapabilityRegistry()
        registry.register_capability(LiveCapability.LIVE_EXECUTION, ADAPTER_ID, requires_approval=False)

        validator = AdapterPreflightValidator(
            real_adapter_policy=policy,
            approval_gate=gate,
            capability_registry=registry,
        )

        # Add a custom check that wraps validate_request (which checks kill switch)
        def kill_switch_check(adapter_id: str, _action: str) -> bool:
            return policy.validate_request(adapter_id, {}).allowed

        validator.add_check("kill_switch", kill_switch_check)

        # First preflight: PASS (may be PARTIAL if credential/network skipped)
        result1 = validator.validate(ADAPTER_ID, ACTION)
        assert result1.status != PreflightStatus.FAIL

        # Activate kill switch
        policy.activate_kill_switch()

        # Second preflight: FAIL — custom kill_switch check blocks
        result2 = validator.validate(ADAPTER_ID, ACTION)
        assert result2.status == PreflightStatus.FAIL
        ks_check = [c for c in result2.checks if c.name == "kill_switch"][0]
        assert ks_check.passed is False


class TestCapabilityRevoked:
    """Register then deny capability → is_allowed blocks."""

    def test_denied_capability_blocks(self):
        registry = LiveCapabilityRegistry()
        registry.register_capability(LiveCapability.LIVE_EXECUTION, ADAPTER_ID, requires_approval=False)

        assert registry.is_allowed(LiveCapability.LIVE_EXECUTION, ADAPTER_ID) is True

        # Deny
        registry.deny_capability(LiveCapability.LIVE_EXECUTION, ADAPTER_ID)

        assert registry.is_allowed(LiveCapability.LIVE_EXECUTION, ADAPTER_ID) is False

    def test_denied_capability_fails_preflight(self):
        policy = RealAdapterPolicy()
        policy.register(ADAPTER_ID, {"endpoint": "https://sandbox.example.com"})
        policy.add_to_allowlist(ADAPTER_ID)

        gate = ManualApprovalGate()
        token = gate.request_approval(ACTION, ADAPTER_ID)
        gate.approve(token)

        registry = LiveCapabilityRegistry()
        registry.register_capability(LiveCapability.LIVE_EXECUTION, ADAPTER_ID, requires_approval=False)

        validator = AdapterPreflightValidator(
            real_adapter_policy=policy,
            approval_gate=gate,
            capability_registry=registry,
        )

        # Preflight passes
        result1 = validator.validate(ADAPTER_ID, ACTION)
        cap_check1 = [c for c in result1.checks if c.name == "capability"][0]
        assert cap_check1.passed is True

        # Deny capability
        registry.deny_capability(LiveCapability.LIVE_EXECUTION, ADAPTER_ID)

        # Preflight fails
        result2 = validator.validate(ADAPTER_ID, ACTION)
        assert result2.status == PreflightStatus.FAIL
        cap_check2 = [c for c in result2.checks if c.name == "capability"][0]
        assert cap_check2.passed is False


class TestApprovalExpired:
    """Approval with ttl_seconds=0 expires immediately."""

    def test_expired_approval_is_not_approved(self):
        gate = ManualApprovalGate()
        token = gate.request_approval(ACTION, ADAPTER_ID, ttl_seconds=0)

        # Approve immediately
        gate.approve(token)

        # Force time past expiry (ttl=0 means expires_at = now)
        # _expire_if_needed runs on access; if time >= expires_at it flips to EXPIRED
        # With ttl=0, expires_at = created_at. Any access after creation checks now >= expires_at.
        # Since time.time() >= created_at (same second or later), it should expire.
        assert gate.is_approved(ACTION, ADAPTER_ID) is False

    def test_expired_approval_fails_preflight(self):
        policy = RealAdapterPolicy()
        policy.register(ADAPTER_ID, {"endpoint": "https://sandbox.example.com"})
        policy.add_to_allowlist(ADAPTER_ID)

        gate = ManualApprovalGate()
        token = gate.request_approval(ACTION, ADAPTER_ID, ttl_seconds=0)
        gate.approve(token)

        registry = LiveCapabilityRegistry()
        registry.register_capability(LiveCapability.LIVE_EXECUTION, ADAPTER_ID, requires_approval=False)

        validator = AdapterPreflightValidator(
            real_adapter_policy=policy,
            approval_gate=gate,
            capability_registry=registry,
        )

        result = validator.validate(ADAPTER_ID, ACTION)
        assert result.status == PreflightStatus.FAIL
        approval_check = [c for c in result.checks if c.name == "approval"][0]
        assert approval_check.passed is False


class TestApprovalConsumedBlocks:
    """Single-use token: consume once, second attempt fails."""

    def test_consume_twice_fails(self):
        gate = ManualApprovalGate()
        token = gate.request_approval(ACTION, ADAPTER_ID, ttl_seconds=3600)
        gate.approve(token)

        # First consume: success
        result1 = gate.consume(token)
        assert result1.success is True
        assert result1.status == ApprovalStatus.CONSUMED

        # Second consume: fail
        result2 = gate.consume(token)
        assert result2.success is False
        assert result2.detail == "token already consumed"

    def test_consumed_token_not_approved(self):
        gate = ManualApprovalGate()
        token = gate.request_approval(ACTION, ADAPTER_ID, ttl_seconds=3600)
        gate.approve(token)

        gate.consume(token)

        # is_approved returns False after consumption
        assert gate.is_approved(ACTION, ADAPTER_ID) is False

    def test_consumed_token_fails_preflight(self):
        policy = RealAdapterPolicy()
        policy.register(ADAPTER_ID, {"endpoint": "https://sandbox.example.com"})
        policy.add_to_allowlist(ADAPTER_ID)

        gate = ManualApprovalGate()
        token = gate.request_approval(ACTION, ADAPTER_ID, ttl_seconds=3600)
        gate.approve(token)
        gate.consume(token)

        registry = LiveCapabilityRegistry()
        registry.register_capability(LiveCapability.LIVE_EXECUTION, ADAPTER_ID, requires_approval=False)

        validator = AdapterPreflightValidator(
            real_adapter_policy=policy,
            approval_gate=gate,
            capability_registry=registry,
        )

        result = validator.validate(ADAPTER_ID, ACTION)
        assert result.status == PreflightStatus.FAIL
        approval_check = [c for c in result.checks if c.name == "approval"][0]
        assert approval_check.passed is False


class TestBudgetExceeded:
    """Low ceiling ($0.01) + $0.02 request → within_budget=False."""

    def test_budget_exceeded_blocks(self):
        policy = RealAdapterPolicy()
        policy._budget_ceilings[ADAPTER_ID] = 0.01

        result = policy.check_budget_ceiling(
            adapter_id=ADAPTER_ID,
            current_cost_usd=0.0,
            request_cost_usd=0.02,
        )

        assert result.within_budget is False
        assert result.ceiling == 0.01
        assert result.current_cost == 0.0
        assert result.request_cost == 0.02

    def test_budget_within_limit_passes(self):
        policy = RealAdapterPolicy()
        policy._budget_ceilings[ADAPTER_ID] = 1.0

        result = policy.check_budget_ceiling(
            adapter_id=ADAPTER_ID,
            current_cost_usd=0.0,
            request_cost_usd=0.5,
        )

        assert result.within_budget is True


class TestCircuitOpen:
    """Record enough failures to open circuit → blocks tasks."""

    def test_circuit_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

        for _ in range(3):
            cb.record_failure(reason="test error")

        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_circuit_closed_allows_requests(self):
        cb = CircuitBreaker(failure_threshold=5)

        # Under threshold: still CLOSED
        for _ in range(4):
            cb.record_failure(reason="partial")

        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_circuit_half_open_after_recovery(self):
        # Use large timeout so state stays OPEN after failures
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=9999.0)

        cb.record_failure(reason="e1")
        cb.record_failure(reason="e2")
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

        # Force transition to HALF_OPEN by resetting the last_failure_time
        cb._last_failure_time = time.monotonic() - 99999
        state = cb.state
        assert state == CircuitState.HALF_OPEN
        assert cb.allow_request() is True  # half_open_max=1 by default

    def test_circuit_trip_force_opens(self):
        cb = CircuitBreaker(failure_threshold=100)

        # Force trip without hitting threshold
        cb.trip(reason="manual safety trip")

        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False
