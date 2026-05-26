"""Unit tests for RealAdapterPolicy."""

import time

import pytest

from core.real_adapter_policy import (
    AdapterPolicyResult,
    BudgetCheckResult,
    RealAdapterPolicy,
)


@pytest.fixture
def policy() -> RealAdapterPolicy:
    return RealAdapterPolicy()


GOOD_CONFIG = {"endpoint": "https://sandbox.example.com/api/v1"}
BAD_CONFIG_NO_ENDPOINT = {}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_unregistered_adapter_blocked(self, policy: RealAdapterPolicy) -> None:
        result = policy.validate_request("unknown", {"action": "trade"})
        assert not result.allowed
        assert any(v.rule == "not_registered" for v in result.violations)

    def test_registered_adapter_on_allowlist_allowed(
        self, policy: RealAdapterPolicy
    ) -> None:
        policy.register("alpha", GOOD_CONFIG)
        policy.add_to_allowlist("alpha")
        result = policy.validate_request("alpha", {"action": "trade"})
        assert result.allowed
        assert len(result.violations) == 0

    def test_registration_rejects_missing_endpoint(self, policy: RealAdapterPolicy) -> None:
        result = policy.validate_adapter_registration("alpha", {"api_key": "k"})
        assert not result.allowed
        assert any(v.rule == "endpoint_required" for v in result.violations)

    def test_registration_rejects_empty_id(self, policy: RealAdapterPolicy) -> None:
        result = policy.validate_adapter_registration("", GOOD_CONFIG)
        assert not result.allowed
        assert any(v.rule == "adapter_id_required" for v in result.violations)

    def test_registration_rejects_non_dict_config(self, policy: RealAdapterPolicy) -> None:
        result = policy.validate_adapter_registration("alpha", None)
        assert not result.allowed
        assert any(v.rule == "config_required" for v in result.violations)


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------

class TestAllowlist:
    def test_add_to_allowlist(self, policy: RealAdapterPolicy) -> None:
        policy.add_to_allowlist("alpha")
        assert policy.is_allowed("alpha")

    def test_remove_from_allowlist(self, policy: RealAdapterPolicy) -> None:
        policy.add_to_allowlist("alpha")
        policy.remove_from_allowlist("alpha")
        assert not policy.is_allowed("alpha")

    def test_not_on_allowlist_blocked(self, policy: RealAdapterPolicy) -> None:
        policy.register("alpha", GOOD_CONFIG)
        result = policy.validate_request("alpha", {"action": "trade"})
        assert not result.allowed
        assert any(v.rule == "not_on_allowlist" for v in result.violations)

    def test_remove_nonexistent_no_error(self, policy: RealAdapterPolicy) -> None:
        policy.remove_from_allowlist("ghost")
        assert not policy.is_allowed("ghost")


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

class TestBudgetCeiling:
    def test_within_budget(self, policy: RealAdapterPolicy) -> None:
        r = policy.check_budget_ceiling("alpha", 5.0, 3.0)
        assert isinstance(r, BudgetCheckResult)
        assert r.within_budget
        assert r.current_cost == 5.0
        assert r.request_cost == 3.0
        assert r.ceiling == 10.0

    def test_exceeds_budget(self, policy: RealAdapterPolicy) -> None:
        r = policy.check_budget_ceiling("alpha", 9.0, 2.0)
        assert not r.within_budget
        assert r.ceiling == 10.0
        assert r.current_cost == 9.0

    def test_exact_budget_boundary(self, policy: RealAdapterPolicy) -> None:
        r = policy.check_budget_ceiling("alpha", 8.0, 2.0)
        assert r.within_budget

    def test_cost_not_advanced_when_exceeded(self, policy: RealAdapterPolicy) -> None:
        policy.check_budget_ceiling("alpha", 9.0, 2.0)
        r2 = policy.check_budget_ceiling("alpha", 9.0, 0.5)
        assert r2.within_budget


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------

class TestRateLimit:
    def test_within_limit(self, policy: RealAdapterPolicy) -> None:
        assert policy.check_rate_limit("alpha")

    def test_exceeds_limit(self, policy: RealAdapterPolicy) -> None:
        for _ in range(10):
            policy.check_rate_limit("alpha")
        assert not policy.check_rate_limit("alpha")


# ---------------------------------------------------------------------------
# Kill switch
# ---------------------------------------------------------------------------

class TestKillSwitch:
    def test_global_kill_switch_blocks_all(self, policy: RealAdapterPolicy) -> None:
        policy.register("alpha", GOOD_CONFIG)
        policy.add_to_allowlist("alpha")
        policy.activate_kill_switch()
        result = policy.validate_request("alpha", {"action": "trade"})
        assert not result.allowed
        assert any(v.rule == "kill_switch_global" for v in result.violations)

    def test_specific_kill_switch_blocks_adapter(
        self, policy: RealAdapterPolicy
    ) -> None:
        policy.register("alpha", GOOD_CONFIG)
        policy.register("beta", GOOD_CONFIG)
        policy.add_to_allowlist("alpha")
        policy.add_to_allowlist("beta")
        policy.activate_kill_switch("alpha")
        assert policy.is_kill_switch_active("alpha")
        assert not policy.is_kill_switch_active("beta")
        r1 = policy.validate_request("alpha", {"action": "trade"})
        r2 = policy.validate_request("beta", {"action": "trade"})
        assert not r1.allowed
        assert r2.allowed

    def test_deactivate_global_restores_access(
        self, policy: RealAdapterPolicy
    ) -> None:
        policy.register("alpha", GOOD_CONFIG)
        policy.add_to_allowlist("alpha")
        policy.activate_kill_switch()
        policy.deactivate_kill_switch()
        assert not policy.is_kill_switch_active("alpha")
        result = policy.validate_request("alpha", {"action": "trade"})
        assert result.allowed

    def test_deactivate_specific_restores_adapter(
        self, policy: RealAdapterPolicy
    ) -> None:
        policy.register("alpha", GOOD_CONFIG)
        policy.add_to_allowlist("alpha")
        policy.activate_kill_switch("alpha")
        policy.deactivate_kill_switch("alpha")
        assert not policy.is_kill_switch_active("alpha")

    def test_deactivate_global_clears_all_specific(
        self, policy: RealAdapterPolicy
    ) -> None:
        policy.activate_kill_switch("alpha")
        policy.activate_kill_switch("beta")
        policy.deactivate_kill_switch()
        assert not policy.is_kill_switch_active("alpha")
        assert not policy.is_kill_switch_active("beta")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_output(self, policy: RealAdapterPolicy) -> None:
        policy.register("alpha", GOOD_CONFIG)
        policy.add_to_allowlist("alpha")
        s = policy.summary()
        assert isinstance(s, dict)
        assert "alpha" in s["registered"]
        assert "alpha" in s["allowlist"]
        assert s["kill_switch_global"] is False
        assert s["default_budget_ceiling"] == 10.0
        assert s["default_rate_limit"] == 10


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------

class TestIsolation:
    def test_multiple_adapters_isolated(self, policy: RealAdapterPolicy) -> None:
        policy.register("alpha", GOOD_CONFIG)
        policy.register("beta", GOOD_CONFIG)
        policy.add_to_allowlist("alpha")
        policy.add_to_allowlist("beta")
        policy.activate_kill_switch("alpha")
        assert not policy.is_kill_switch_active("beta")
        r1 = policy.validate_request("alpha", {"action": "trade"})
        r2 = policy.validate_request("beta", {"action": "trade"})
        assert not r1.allowed
        assert r2.allowed

    def test_credential_isolation_config(self, policy: RealAdapterPolicy) -> None:
        config_a = {
            "endpoint": "https://a.example.com",
            "api_key": "secret-a",
        }
        config_b = {
            "endpoint": "https://b.example.com",
            "api_key": "secret-b",
        }
        policy.register("alpha", config_a)
        policy.register("beta", config_b)
        a_cfg = policy.get_adapter_config("alpha")
        b_cfg = policy.get_adapter_config("beta")
        assert a_cfg is not None
        assert b_cfg is not None
        assert a_cfg["api_key"] == "secret-a"
        assert b_cfg["api_key"] == "secret-b"

    def test_credential_isolation_cross_ref_blocked(
        self, policy: RealAdapterPolicy
    ) -> None:
        bad_config = {
            "endpoint": "https://a.example.com",
            "cross_adapter_refs": {"alpha": True},
        }
        result = policy.validate_adapter_registration("beta", bad_config)
        assert not result.allowed
        assert any(v.rule == "credential_isolation" for v in result.violations)

    def test_request_level_credential_isolation(
        self, policy: RealAdapterPolicy
    ) -> None:
        policy.register("alpha", GOOD_CONFIG)
        policy.add_to_allowlist("alpha")
        result = policy.validate_request(
            "alpha",
            {"action": "trade", "access_other_adapter_config": True},
        )
        assert not result.allowed
        assert any(v.rule == "credential_isolation" for v in result.violations)

    def test_unknown_adapter_get_config_returns_none(
        self, policy: RealAdapterPolicy
    ) -> None:
        assert policy.get_adapter_config("ghost") is None
