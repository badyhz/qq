"""Tests for AdapterPreflightValidator."""

import pytest
import os

from core.adapter_preflight import (
    AdapterPreflightValidator,
    PreflightResult,
    PreflightCheck,
    PreflightStatus,
)
from core.credential_manager import CredentialManager
from core.network_sandbox import NetworkSandbox
from core.real_adapter_policy import RealAdapterPolicy
from core.manual_approval_gate import ManualApprovalGate
from core.live_capability_registry import LiveCapability, LiveCapabilityRegistry


# ── helpers ────────────────────────────────────────────────────────


def _make_full_validator(**overrides):
    """Build a validator with all deps wired up for adapter_id='test_adapter'."""
    cm = CredentialManager()
    cm.register_adapter("test_adapter", env_var="QQ_TEST_KEY")
    os.environ["QQ_TEST_KEY"] = "dummy_value_12345678"

    ns = NetworkSandbox(mode="simulation")

    rap = RealAdapterPolicy()
    rap.add_to_allowlist("test_adapter")

    reg = LiveCapabilityRegistry()
    reg.register_capability(LiveCapability.LIVE_EXECUTION, "test_adapter")

    ag = ManualApprovalGate()
    token = ag.request_approval("default", "test_adapter")
    ag.approve(token)

    return AdapterPreflightValidator(
        credential_manager=overrides.get("credential_manager", cm),
        network_sandbox=overrides.get("network_sandbox", ns),
        real_adapter_policy=overrides.get("real_adapter_policy", rap),
        approval_gate=overrides.get("approval_gate", ag),
        capability_registry=overrides.get("capability_registry", reg),
    )


# ── tests ──────────────────────────────────────────────────────────


class TestPreflightPass:
    def test_all_checks_pass(self):
        v = _make_full_validator()
        result = v.validate("test_adapter")
        assert result.status == PreflightStatus.PASS
        assert all(c.passed for c in result.checks)
        assert result.timestamp > 0

    def test_all_deps_present_all_checks_run(self):
        v = _make_full_validator()
        result = v.validate("test_adapter")
        names = [c.name for c in result.checks]
        assert "skipped" not in " ".join(c.detail for c in result.checks)
        assert len(result.checks) == 5


class TestPreflightPartial:
    def test_no_deps_gives_partial(self):
        v = AdapterPreflightValidator()
        result = v.validate("anything")
        assert result.status == PreflightStatus.PARTIAL
        assert all(c.passed for c in result.checks)

    def test_only_credential_manager(self):
        cm = CredentialManager()
        cm.register_adapter("test_adapter", env_var="QQ_MISSING_KEY_FOR_TEST")
        v = AdapterPreflightValidator(credential_manager=cm)
        result = v.validate("test_adapter")
        assert result.status == PreflightStatus.FAIL  # credential missing from env

    def test_missing_dependency_skips_check(self):
        v = AdapterPreflightValidator()
        result = v.validate("test_adapter")
        details = [c.detail for c in result.checks]
        assert any("skipped" in d for d in details)


class TestPreflightFail:
    def test_credential_missing(self):
        cm = CredentialManager()
        cm.register_adapter("test_adapter", env_var="QQ_NONEXISTENT")
        v = AdapterPreflightValidator(credential_manager=cm)
        result = v.validate("test_adapter")
        assert result.status == PreflightStatus.FAIL
        cred_check = [c for c in result.checks if c.name == "credential"][0]
        assert not cred_check.passed

    def test_network_offline(self):
        ns = NetworkSandbox(mode="offline")
        v = AdapterPreflightValidator(network_sandbox=ns)
        result = v.validate("test_adapter")
        assert result.status == PreflightStatus.FAIL
        net_check = [c for c in result.checks if c.name == "network"][0]
        assert not net_check.passed

    def test_capability_denied(self):
        reg = LiveCapabilityRegistry()
        # not registered
        v = AdapterPreflightValidator(capability_registry=reg)
        result = v.validate("test_adapter")
        assert result.status == PreflightStatus.FAIL
        cap_check = [c for c in result.checks if c.name == "capability"][0]
        assert not cap_check.passed

    def test_approval_missing(self):
        ag = ManualApprovalGate()
        v = AdapterPreflightValidator(approval_gate=ag)
        result = v.validate("test_adapter", action="default")
        assert result.status == PreflightStatus.FAIL
        apr_check = [c for c in result.checks if c.name == "approval"][0]
        assert not apr_check.passed

    def test_allowlist_missing(self):
        rap = RealAdapterPolicy()
        v = AdapterPreflightValidator(real_adapter_policy=rap)
        result = v.validate("test_adapter")
        assert result.status == PreflightStatus.FAIL
        bud_check = [c for c in result.checks if c.name == "budget"][0]
        assert not bud_check.passed


class TestCustomChecks:
    def test_custom_check_passes(self):
        v = AdapterPreflightValidator()
        v.add_check("env_check", lambda aid, act: True)
        result = v.validate("test_adapter")
        custom = [c for c in result.checks if c.name == "env_check"][0]
        assert custom.passed

    def test_custom_check_fails(self):
        v = AdapterPreflightValidator()
        v.add_check("env_check", lambda aid, act: False)
        result = v.validate("test_adapter")
        assert result.status == PreflightStatus.FAIL
        custom = [c for c in result.checks if c.name == "env_check"][0]
        assert not custom.passed

    def test_custom_check_exception(self):
        v = AdapterPreflightValidator()
        v.add_check("boom", lambda aid, act: 1 / 0)
        result = v.validate("test_adapter")
        assert result.status == PreflightStatus.FAIL
        boom = [c for c in result.checks if c.name == "boom"][0]
        assert not boom.passed
        assert "division by zero" in boom.detail

    def test_add_and_remove(self):
        v = AdapterPreflightValidator()
        v.add_check("x", lambda aid, act: True)
        assert "x" in v.summary()["custom_checks"]
        v.remove_check("x")
        assert "x" not in v.summary()["custom_checks"]

    def test_remove_nonexistent(self):
        v = AdapterPreflightValidator()
        v.remove_check("nope")  # should not raise


class TestSummary:
    def test_summary_all_none(self):
        v = AdapterPreflightValidator()
        s = v.summary()
        assert s["credential_manager"] is False
        assert s["network_sandbox"] is False
        assert s["real_adapter_policy"] is False
        assert s["approval_gate"] is False
        assert s["capability_registry"] is False
        assert s["custom_checks"] == []

    def test_summary_all_set(self):
        v = _make_full_validator()
        s = v.summary()
        assert all(v is True for k, v in s.items() if k != "custom_checks")


class TestMultipleAdapters:
    def test_independent_adapters(self):
        cm = CredentialManager()
        cm.register_adapter("adapter_a", env_var="QQ_KEY_A")
        os.environ["QQ_KEY_A"] = "key_a_value_12345"

        v = AdapterPreflightValidator(credential_manager=cm)

        # adapter_a has credential
        result_a = v.validate("adapter_a")
        cred_a = [c for c in result_a.checks if c.name == "credential"][0]
        assert cred_a.passed

        # adapter_b not registered -> no credential
        result_b = v.validate("adapter_b")
        cred_b = [c for c in result_b.checks if c.name == "credential"][0]
        assert not cred_b.passed

        assert result_a.status == PreflightStatus.PARTIAL  # other checks skipped
        assert result_b.status == PreflightStatus.FAIL  # credential failed
