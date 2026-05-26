"""Unit tests for LiveCapabilityRegistry."""

import pytest

from core.live_capability_registry import (
    CapabilityRecord,
    CapabilityValidationResult,
    LiveCapability,
    LiveCapabilityRegistry,
)


class TestLiveCapabilityEnum:
    """Verify enum values."""

    def test_enum_values(self):
        assert LiveCapability.NETWORK_CALL.value == "network_call"
        assert LiveCapability.REAL_API.value == "real_api"
        assert LiveCapability.REAL_CREDENTIAL.value == "real_credential"
        assert LiveCapability.LIVE_EXECUTION.value == "live_execution"
        assert LiveCapability.DATA_WRITE.value == "data_write"

    def test_enum_count(self):
        assert len(LiveCapability) == 5


class TestDefaultBehavior:
    """All capabilities denied by default."""

    def test_no_capabilities_allowed(self):
        reg = LiveCapabilityRegistry()
        for cap in LiveCapability:
            assert reg.has_capability(cap, "any_adapter") is False
            assert reg.is_allowed(cap, "any_adapter") is False

    def test_requires_approval_true_for_unknown(self):
        reg = LiveCapabilityRegistry()
        assert reg.requires_approval(LiveCapability.NETWORK_CALL, "unknown") is True


class TestRegisterCapability:
    """Registering a capability."""

    def test_register_makes_has_capability_true(self):
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.NETWORK_CALL, "adapter_a")
        assert reg.has_capability(LiveCapability.NETWORK_CALL, "adapter_a") is True

    def test_is_allowed_for_registered_non_denied(self):
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.REAL_API, "adapter_a")
        assert reg.is_allowed(LiveCapability.REAL_API, "adapter_a") is True

    def test_is_allowed_false_for_unregistered(self):
        reg = LiveCapabilityRegistry()
        assert reg.is_allowed(LiveCapability.REAL_API, "adapter_a") is False

    def test_register_without_approval(self):
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.DATA_WRITE, "adapter_a", requires_approval=False)
        assert reg.requires_approval(LiveCapability.DATA_WRITE, "adapter_a") is False


class TestDenyCapability:
    """Denying a capability."""

    def test_deny_blocks_even_if_registered(self):
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.LIVE_EXECUTION, "adapter_a")
        assert reg.is_allowed(LiveCapability.LIVE_EXECUTION, "adapter_a") is True
        reg.deny_capability(LiveCapability.LIVE_EXECUTION, "adapter_a")
        assert reg.is_allowed(LiveCapability.LIVE_EXECUTION, "adapter_a") is False
        assert reg.has_capability(LiveCapability.LIVE_EXECUTION, "adapter_a") is True

    def test_deny_unregistered(self):
        reg = LiveCapabilityRegistry()
        reg.deny_capability(LiveCapability.NETWORK_CALL, "adapter_a")
        assert reg.is_allowed(LiveCapability.NETWORK_CALL, "adapter_a") is False
        assert reg.has_capability(LiveCapability.NETWORK_CALL, "adapter_a") is False

    def test_reinstate_removes_deny(self):
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.REAL_CREDENTIAL, "adapter_a")
        reg.deny_capability(LiveCapability.REAL_CREDENTIAL, "adapter_a")
        assert reg.is_allowed(LiveCapability.REAL_CREDENTIAL, "adapter_a") is False
        reg.reinstate_capability(LiveCapability.REAL_CREDENTIAL, "adapter_a")
        assert reg.is_allowed(LiveCapability.REAL_CREDENTIAL, "adapter_a") is True

    def test_reinstate_nonexistent_no_error(self):
        reg = LiveCapabilityRegistry()
        reg.reinstate_capability(LiveCapability.NETWORK_CALL, "ghost")
        assert reg.is_allowed(LiveCapability.NETWORK_CALL, "ghost") is False


class TestListCapabilities:
    """Listing capabilities."""

    def test_list_empty(self):
        reg = LiveCapabilityRegistry()
        assert reg.list_capabilities() == {}

    def test_list_all(self):
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.NETWORK_CALL, "a1")
        reg.register_capability(LiveCapability.DATA_WRITE, "a1")
        reg.register_capability(LiveCapability.REAL_API, "a2")
        caps = reg.list_capabilities()
        assert "a1" in caps
        assert "a2" in caps
        assert len(caps) == 2

    def test_list_filtered_by_adapter(self):
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.NETWORK_CALL, "a1")
        reg.register_capability(LiveCapability.REAL_API, "a2")
        caps = reg.list_capabilities(adapter_id="a1")
        assert "a1" in caps
        assert "a2" not in caps


class TestValidateAll:
    """Validate all adapters."""

    def test_fully_approved_adapter(self):
        reg = LiveCapabilityRegistry()
        for cap in LiveCapability:
            reg.register_capability(cap, "adapter_a", requires_approval=False)
        result = reg.validate_all(["adapter_a"])
        assert result.valid is True
        assert "adapter_a" in result.approved
        assert result.denied == []
        assert result.unregistered == []

    def test_denied_capability_makes_invalid(self):
        reg = LiveCapabilityRegistry()
        for cap in LiveCapability:
            reg.register_capability(cap, "adapter_a")
        reg.deny_capability(LiveCapability.LIVE_EXECUTION, "adapter_a")
        result = reg.validate_all(["adapter_a"])
        assert result.valid is False
        assert "adapter_a" in result.denied

    def test_unregistered_makes_invalid(self):
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.NETWORK_CALL, "adapter_a")
        # Missing other caps
        result = reg.validate_all(["adapter_a"])
        assert result.valid is False
        assert "adapter_a" in result.unregistered

    def test_multiple_adapters_isolated(self):
        reg = LiveCapabilityRegistry()
        for cap in LiveCapability:
            reg.register_capability(cap, "good_adapter")
        reg.deny_capability(LiveCapability.LIVE_EXECUTION, "bad_adapter")
        result = reg.validate_all(["good_adapter", "bad_adapter"])
        assert result.valid is False
        assert "good_adapter" in result.approved
        assert "bad_adapter" in result.denied


class TestMultipleAdaptersIsolated:
    """Capabilities are isolated per adapter."""

    def test_register_one_adapter_does_not_affect_another(self):
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.NETWORK_CALL, "adapter_x")
        assert reg.is_allowed(LiveCapability.NETWORK_CALL, "adapter_x") is True
        assert reg.is_allowed(LiveCapability.NETWORK_CALL, "adapter_y") is False

    def test_deny_one_adapter_does_not_affect_another(self):
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.REAL_API, "adapter_x")
        reg.register_capability(LiveCapability.REAL_API, "adapter_y")
        reg.deny_capability(LiveCapability.REAL_API, "adapter_x")
        assert reg.is_allowed(LiveCapability.REAL_API, "adapter_x") is False
        assert reg.is_allowed(LiveCapability.REAL_API, "adapter_y") is True


class TestSummary:
    """Summary output."""

    def test_summary_empty(self):
        reg = LiveCapabilityRegistry()
        s = reg.summary()
        assert s["total_records"] == 0
        assert s["registered"] == 0
        assert s["denied"] == 0
        assert s["adapters"] == 0

    def test_summary_populated(self):
        reg = LiveCapabilityRegistry()
        reg.register_capability(LiveCapability.NETWORK_CALL, "a1")
        reg.register_capability(LiveCapability.REAL_API, "a1")
        reg.deny_capability(LiveCapability.LIVE_EXECUTION, "a1")
        reg.register_capability(LiveCapability.NETWORK_CALL, "a2", requires_approval=False)
        s = reg.summary()
        assert s["total_records"] == 4
        assert s["registered"] == 3
        assert s["denied"] == 1
        assert s["requires_approval"] == 3
        assert s["adapters"] == 2
        assert s["capabilities"] == 3


class TestDataclassDefaults:
    """Dataclass record defaults."""

    def test_capability_record_defaults(self):
        rec = CapabilityRecord(
            capability=LiveCapability.NETWORK_CALL,
            adapter_id="test",
        )
        assert rec.registered is False
        assert rec.denied is False
        assert rec.requires_approval is True

    def test_validation_result_defaults(self):
        vr = CapabilityValidationResult(valid=True)
        assert vr.denied == []
        assert vr.unregistered == []
        assert vr.approved == []
