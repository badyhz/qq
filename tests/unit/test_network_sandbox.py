"""Unit tests for core.network_sandbox — no network calls."""

from __future__ import annotations

import pytest

from core.network_sandbox import NetworkCheckResult, NetworkSandbox


class TestDefaultDomains:
    def test_default_allowed_domains(self) -> None:
        sb = NetworkSandbox()
        summary = sb.summary()
        assert "api.anthropic.com" in summary["allowed_domains"]
        assert "api.mimo.example.com" in summary["allowed_domains"]

    def test_default_denied_empty(self) -> None:
        sb = NetworkSandbox()
        summary = sb.summary()
        assert summary["denied_domains"] == []


class TestAddRemoveAllowedDomain:
    def test_add_allowed(self) -> None:
        sb = NetworkSandbox()
        sb.add_allowed_domain("new.example.com")
        assert "new.example.com" in sb.summary()["allowed_domains"]

    def test_remove_allowed(self) -> None:
        sb = NetworkSandbox()
        sb.add_allowed_domain("tmp.example.com")
        sb.remove_allowed_domain("tmp.example.com")
        assert "tmp.example.com" not in sb.summary()["allowed_domains"]

    def test_remove_nonexistent_no_error(self) -> None:
        sb = NetworkSandbox()
        sb.remove_allowed_domain("nonexistent.example.com")  # no error


class TestAddRemoveDeniedDomain:
    def test_add_denied(self) -> None:
        sb = NetworkSandbox()
        sb.add_denied_domain("evil.example.com")
        assert "evil.example.com" in sb.summary()["denied_domains"]

    def test_remove_denied(self) -> None:
        sb = NetworkSandbox()
        sb.add_denied_domain("evil.example.com")
        sb.remove_denied_domain("evil.example.com")
        assert "evil.example.com" not in sb.summary()["denied_domains"]


class TestCheckRequestRestricted:
    def test_allowed_domain(self) -> None:
        sb = NetworkSandbox(mode="restricted")
        result = sb.check_request("https://api.anthropic.com/v1/messages")
        assert result.allowed is True
        assert result.reason == "allowed"
        assert result.domain == "api.anthropic.com"

    def test_denied_domain(self) -> None:
        sb = NetworkSandbox(mode="restricted")
        sb.add_denied_domain("evil.example.com")
        result = sb.check_request("https://evil.example.com/data")
        assert result.allowed is False
        assert result.reason == "denied_by_denylist"
        assert result.domain == "evil.example.com"

    def test_unknown_domain_not_in_allowlist(self) -> None:
        sb = NetworkSandbox(mode="restricted")
        result = sb.check_request("https://unknown.example.com/api")
        assert result.allowed is False
        assert result.reason == "not_in_allowlist"
        assert result.domain == "unknown.example.com"


class TestCheckRequestOffline:
    def test_always_blocked(self) -> None:
        sb = NetworkSandbox(mode="offline")
        result = sb.check_request("https://api.anthropic.com/v1/messages")
        assert result.allowed is False
        assert result.reason == "offline_mode"

    def test_any_domain_blocked(self) -> None:
        sb = NetworkSandbox(mode="offline")
        sb.add_allowed_domain("anything.com")
        result = sb.check_request("https://anything.com/x")
        assert result.allowed is False


class TestCheckRequestSimulation:
    def test_always_allowed(self) -> None:
        sb = NetworkSandbox(mode="simulation")
        result = sb.check_request("https://random.example.com/anything")
        assert result.allowed is True
        assert result.reason == "simulation_mode"


class TestRateCeiling:
    def test_within_limit(self) -> None:
        sb = NetworkSandbox(mode="restricted")
        sb.set_rate_ceiling("api.anthropic.com", 5)
        # 4 requests so far
        assert sb.check_rate_ceiling("api.anthropic.com", 4) is True

    def test_exceeds_limit(self) -> None:
        sb = NetworkSandbox(mode="restricted")
        sb.set_rate_ceiling("api.anthropic.com", 5)
        assert sb.check_rate_ceiling("api.anthropic.com", 5) is False

    def test_check_request_rate_exceeded(self) -> None:
        sb = NetworkSandbox(mode="restricted")
        sb.set_rate_ceiling("api.anthropic.com", 3)
        # record 3 requests
        for _ in range(3):
            sb.record_request("api.anthropic.com")
        result = sb.check_request("https://api.anthropic.com/v1/messages")
        assert result.allowed is False
        assert result.reason == "rate_exceeded"

    def test_set_rate_ceiling_changes_limit(self) -> None:
        sb = NetworkSandbox(mode="restricted")
        # default ceiling is 100
        assert sb.check_rate_ceiling("api.anthropic.com", 99) is True
        sb.set_rate_ceiling("api.anthropic.com", 10)
        assert sb.check_rate_ceiling("api.anthropic.com", 99) is False
        assert sb.check_rate_ceiling("api.anthropic.com", 9) is True


class TestRecordRequest:
    def test_record_request_increments(self) -> None:
        sb = NetworkSandbox()
        sb.record_request("api.anthropic.com")
        sb.record_request("api.anthropic.com")
        assert sb.summary()["request_counts"]["api.anthropic.com"] == 2


class TestIsAllowed:
    def test_quick_check(self) -> None:
        sb = NetworkSandbox(mode="restricted")
        assert sb.is_allowed("https://api.anthropic.com/v1") is True
        assert sb.is_allowed("https://unknown.example.com") is False


class TestMultipleDomainsIndependent:
    def test_rate_independent(self) -> None:
        sb = NetworkSandbox(mode="restricted")
        sb.add_allowed_domain("a.example.com")
        sb.add_allowed_domain("b.example.com")
        sb.set_rate_ceiling("a.example.com", 2)
        sb.set_rate_ceiling("b.example.com", 2)
        sb.record_request("a.example.com")
        sb.record_request("a.example.com")
        # a is at limit
        assert sb.check_request("https://a.example.com/x").allowed is False
        # b is still fine
        assert sb.check_request("https://b.example.com/x").allowed is True


class TestModeSwitching:
    def test_switch_modes(self) -> None:
        sb = NetworkSandbox(mode="restricted")
        sb.set_mode("offline")
        assert sb.is_allowed("https://api.anthropic.com/x") is False
        sb.set_mode("simulation")
        assert sb.is_allowed("https://anything.com/x") is True
        sb.set_mode("restricted")
        assert sb.is_allowed("https://api.anthropic.com/x") is True

    def test_invalid_mode_raises(self) -> None:
        sb = NetworkSandbox()
        with pytest.raises(ValueError, match="Invalid mode"):
            sb.set_mode("live")
        with pytest.raises(ValueError, match="Invalid mode"):
            NetworkSandbox(mode="live")


class TestSummary:
    def test_summary_structure(self) -> None:
        sb = NetworkSandbox()
        s = sb.summary()
        assert "mode" in s
        assert "allowed_domains" in s
        assert "denied_domains" in s
        assert "rate_ceilings" in s
        assert "default_rate_ceiling" in s
        assert "request_counts" in s


class TestCheckResultDataclass:
    def test_fields(self) -> None:
        r = NetworkCheckResult(allowed=True, reason="allowed", domain="test.com")
        assert r.allowed is True
        assert r.reason == "allowed"
        assert r.domain == "test.com"
