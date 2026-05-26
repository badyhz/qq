"""Tests for adapters/live_adapter_transport.py."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from adapters.live_adapter_transport import (
    DryRunTransport,
    DryRunTransportResponse,
    LiveAdapterTransport,
    TransportResult,
)
from core.credential_manager import CredentialManager
from core.network_sandbox import NetworkSandbox


# ── stubs ───────────────────────────────────────────────────────────────

@dataclass
class _StubResponse:
    status_code: int = 200
    body: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


class _SuccessTransport:
    async def request(self, method: str, url: str, headers: dict | None = None, body: dict | None = None) -> _StubResponse:
        return _StubResponse(status_code=200, body={"ok": True})


class _FailTransport:
    async def request(self, method: str, url: str, headers: dict | None = None, body: dict | None = None) -> _StubResponse:
        raise ConnectionError("simulated failure")


class _ErrTransport:
    async def request(self, method: str, url: str, headers: dict | None = None, body: dict | None = None) -> _StubResponse:
        return _StubResponse(status_code=500, body={"error": "internal"})


def _make_cm(env_var: str = "TEST_API_KEY") -> CredentialManager:
    cm = CredentialManager()
    cm.register_adapter("test_adapter", env_var)
    return cm


def _make_sandbox(allowed: bool = True) -> NetworkSandbox:
    sb = NetworkSandbox(mode="restricted" if allowed else "offline")
    if allowed:
        sb.add_allowed_domain("example.com")
    return sb


# ── tests ───────────────────────────────────────────────────────────────

class TestSendRequestSuccess:
    @pytest.mark.anyio
    async def test_all_checks_pass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_API_KEY", "sk-test-1234567890")
        cm = _make_cm()
        transport = LiveAdapterTransport(_SuccessTransport(), credential_manager=cm)
        result = await transport.send_request("test_adapter", "GET", "https://example.com/api")
        assert result.success is True
        assert result.response is not None
        assert result.response.status_code == 200
        assert result.preflight_passed is True
        assert result.network_allowed is True
        assert result.credential_available is True
        assert result.error is None

    @pytest.mark.anyio
    async def test_no_governance_components(self) -> None:
        transport = LiveAdapterTransport(_SuccessTransport())
        result = await transport.send_request("any", "GET", "https://example.com")
        assert result.success is True
        assert result.preflight_passed is True
        assert result.network_allowed is True
        assert result.credential_available is True


class TestMissingCredential:
    @pytest.mark.anyio
    async def test_missing_credential_returns_error(self) -> None:
        cm = _make_cm()
        transport = LiveAdapterTransport(_SuccessTransport(), credential_manager=cm)
        # env var not set
        result = await transport.send_request("test_adapter", "GET", "https://example.com")
        assert result.success is False
        assert result.error is not None
        assert "missing credential" in result.error
        assert result.credential_available is False


class TestNetworkSandbox:
    @pytest.mark.anyio
    async def test_blocked_url_returns_error(self) -> None:
        sb = NetworkSandbox(mode="restricted")
        sb.add_denied_domain("evil.com")
        transport = LiveAdapterTransport(_SuccessTransport(), network_sandbox=sb)
        result = await transport.send_request("any", "POST", "https://evil.com/payload")
        assert result.success is False
        assert result.error is not None
        assert "blocked" in result.error
        assert result.network_allowed is False

    @pytest.mark.anyio
    async def test_allowed_url_passes(self) -> None:
        sb = _make_sandbox(allowed=True)
        transport = LiveAdapterTransport(_SuccessTransport(), network_sandbox=sb)
        result = await transport.send_request("any", "GET", "https://example.com/api")
        assert result.network_allowed is True
        assert result.success is True


class TestPreflightFailure:
    @pytest.mark.anyio
    async def test_preflight_fail_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.adapter_preflight import AdapterPreflightValidator
        monkeypatch.setenv("TEST_API_KEY", "sk-test-1234567890")
        cm = _make_cm()
        sb = _make_sandbox(allowed=True)
        pf = AdapterPreflightValidator(credential_manager=cm, network_sandbox=sb)
        # add a custom check that always fails for this adapter
        pf.add_check("always_fail", lambda aid, action: False)
        transport = LiveAdapterTransport(
            _SuccessTransport(), credential_manager=cm,
            network_sandbox=sb, preflight_validator=pf,
        )
        result = await transport.send_request("test_adapter", "GET", "https://example.com/api")
        assert result.success is False
        assert result.error is not None
        assert "preflight" in result.error
        assert result.preflight_passed is False


class TestHeadersIncludeAuth:
    @pytest.mark.anyio
    async def test_auth_header_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_API_KEY", "sk-secret-key-1234")
        cm = _make_cm()
        transport = LiveAdapterTransport(_SuccessTransport(), credential_manager=cm)
        result = await transport.send_request("test_adapter", "GET", "https://example.com")
        assert result.success is True
        # credential available confirmed
        assert result.credential_available is True

    def test_prepare_headers_includes_bearer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_API_KEY", "sk-secret-key-1234")
        cm = _make_cm()
        transport = LiveAdapterTransport(_SuccessTransport(), credential_manager=cm)
        headers = transport.prepare_headers("test_adapter", {"X-Custom": "val"})
        assert headers["Authorization"] == "Bearer sk-secret-key-1234"
        assert headers["X-Custom"] == "val"

    def test_prepare_headers_no_credential_manager(self) -> None:
        transport = LiveAdapterTransport(_SuccessTransport())
        headers = transport.prepare_headers("any", {"X-Foo": "bar"})
        assert "Authorization" not in headers
        assert headers["X-Foo"] == "bar"


class TestDryRun:
    @pytest.mark.anyio
    async def test_dry_run_logs_without_sending(self) -> None:
        transport = LiveAdapterTransport(_SuccessTransport())
        result = await transport.dry_run("any", "POST", "https://example.com/api", body={"x": 1})
        assert result.success is True
        assert result.response is not None
        assert result.response.body.get("dry_run") is True

    @pytest.mark.anyio
    async def test_dry_run_restores_original_transport(self) -> None:
        original = _SuccessTransport()
        transport = LiveAdapterTransport(original)
        await transport.dry_run("any", "GET", "https://example.com")
        assert transport._transport is original


class TestTransportResultFields:
    def test_default_fields(self) -> None:
        r = TransportResult(success=False)
        assert r.success is False
        assert r.response is None
        assert r.error is None
        assert r.preflight_passed is False
        assert r.network_allowed is False
        assert r.credential_available is False

    def test_all_fields_set(self) -> None:
        resp = _StubResponse(status_code=200)
        r = TransportResult(
            success=True, response=resp, error=None,
            preflight_passed=True, network_allowed=True,
            credential_available=True,
        )
        assert r.success is True
        assert r.response.status_code == 200


class TestTransportError:
    @pytest.mark.anyio
    async def test_transport_exception_captured(self) -> None:
        transport = LiveAdapterTransport(_FailTransport())
        result = await transport.send_request("any", "GET", "https://example.com")
        assert result.success is False
        assert result.error is not None
        assert "ConnectionError" in result.error

    @pytest.mark.anyio
    async def test_5xx_response_not_success(self) -> None:
        transport = LiveAdapterTransport(_ErrTransport())
        result = await transport.send_request("any", "GET", "https://example.com")
        assert result.success is False
        assert result.response is not None
        assert result.response.status_code == 500


class TestRequestLog:
    @pytest.mark.anyio
    async def test_multiple_requests_tracked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_API_KEY", "sk-1234567890")
        cm = _make_cm()
        transport = LiveAdapterTransport(_SuccessTransport(), credential_manager=cm)
        await transport.send_request("test_adapter", "GET", "https://example.com/a")
        await transport.send_request("test_adapter", "POST", "https://example.com/b")
        log = transport.request_log
        assert len(log) == 2
        assert log[0]["url"] == "https://example.com/a"
        assert log[1]["method"] == "POST"

    @pytest.mark.anyio
    async def test_failed_request_logged(self) -> None:
        transport = LiveAdapterTransport(_SuccessTransport())
        sb = NetworkSandbox(mode="restricted")
        # no allowed domains — any URL is blocked
        transport._network_sandbox = sb
        await transport.send_request("any", "GET", "https://unknown.com")
        assert len(transport.request_log) == 1
        assert "error" in transport.request_log[0]


class TestCredentialMasking:
    def test_mask_long_credential(self) -> None:
        masked = CredentialManager.mask_credential("abcdefghij1234")
        assert masked == "abcd***1234"

    def test_mask_short_credential(self) -> None:
        masked = CredentialManager.mask_credential("short")
        assert masked == "***"
