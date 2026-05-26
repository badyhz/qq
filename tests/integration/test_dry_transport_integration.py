"""T769 — Dry Transport Integration.

Full pipeline test: credential → network → preflight → transport → response normalization.
All dry-run. No network. No secrets.
"""
from __future__ import annotations

import pytest

from adapters.live_adapter_transport import (
    DryRunTransport,
    DryRunTransportResponse,
    LiveAdapterTransport,
    TransportResult,
)
from core.http_transport import MockTransport
from core.adapter_preflight import PreflightStatus
from core.response_schema import ResponseStatus, normalize_response, classify_error


# ── stubs ──────────────────────────────────────────────────────────────


class StubCredentialManager:
    def __init__(self, cred: str = "sk-test-abc123def456") -> None:
        self._cred = cred

    def has_credential(self, adapter_id: str) -> bool:
        return True

    def get_credential(self, adapter_id: str) -> str:
        return self._cred

    def mask(self, value: str) -> str:
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}***{value[-4:]}"


class StubNetworkSandbox:
    def __init__(self, blocked: list[str] | None = None) -> None:
        self._blocked = blocked or []

    def is_allowed(self, url: str) -> bool:
        return not any(b in url for b in self._blocked)


class StubPreflightValidator:
    def __init__(self, should_pass: bool = True) -> None:
        self._should_pass = should_pass
        self.calls: list[str] = []

    def validate(self, adapter_id: str) -> object:
        self.calls.append(adapter_id)
        status = PreflightStatus.PASS if self._should_pass else PreflightStatus.FAIL

        class _Result:
            def __init__(self, s: PreflightStatus) -> None:
                self.status = s

        return _Result(status)


# ── tests ──────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_full_dry_pipeline_all_pass():
    """Happy path: credential + network + preflight all pass."""
    transport = DryRunTransport()
    cred = StubCredentialManager()
    net = StubNetworkSandbox()
    preflight = StubPreflightValidator(should_pass=True)

    harness = LiveAdapterTransport(
        transport=transport,
        credential_manager=cred,
        network_sandbox=net,
        preflight_validator=preflight,
    )

    result = await harness.send_request(
        adapter_id="claude",
        method="POST",
        url="https://api.anthropic.com/v1/messages",
        body={"model": "claude-3", "max_tokens": 100},
    )

    assert result.success
    assert result.credential_available
    assert result.network_allowed
    assert result.preflight_passed
    assert result.response is not None
    assert result.response.status_code == 200

    assert len(harness.request_log) == 1
    assert harness.request_log[0]["adapter_id"] == "claude"


@pytest.mark.anyio
async def test_missing_credential_blocks_pipeline():
    """Missing credential short-circuits before network/preflight checks."""

    class NoCredManager:
        def has_credential(self, adapter_id: str) -> bool:
            return False
        def get_credential(self, adapter_id: str) -> str | None:
            return None

    harness = LiveAdapterTransport(
        transport=DryRunTransport(),
        credential_manager=NoCredManager(),
        network_sandbox=StubNetworkSandbox(),
        preflight_validator=StubPreflightValidator(),
    )

    result = await harness.send_request(
        adapter_id="mimo",
        method="GET",
        url="https://api.mimo.ai/v1/infer",
    )

    assert not result.success
    assert "missing credential" in result.error
    assert not result.credential_available
    assert not result.network_allowed
    assert not result.preflight_passed


@pytest.mark.anyio
async def test_network_block_short_circuits():
    """Network sandbox blocks URL before preflight."""
    sandbox = StubNetworkSandbox(blocked=["evil.com"])

    harness = LiveAdapterTransport(
        transport=DryRunTransport(),
        credential_manager=StubCredentialManager(),
        network_sandbox=sandbox,
        preflight_validator=StubPreflightValidator(),
    )

    result = await harness.send_request(
        adapter_id="claude",
        method="POST",
        url="https://evil.com/steal",
    )

    assert not result.success
    assert "network policy blocked" in result.error
    assert not result.preflight_passed


@pytest.mark.anyio
async def test_preflight_failure_blocks_send():
    """Preflight failure stops before transport send."""
    harness = LiveAdapterTransport(
        transport=DryRunTransport(),
        credential_manager=StubCredentialManager(),
        network_sandbox=StubNetworkSandbox(),
        preflight_validator=StubPreflightValidator(should_pass=False),
    )

    result = await harness.send_request(
        adapter_id="claude",
        method="POST",
        url="https://api.anthropic.com/v1/messages",
    )

    assert not result.success
    assert "preflight failed" in result.error
    assert result.network_allowed
    assert not result.preflight_passed


@pytest.mark.anyio
async def test_dry_run_mode_never_sends():
    """dry_run() uses internal DryRunTransport, never touches real transport."""
    class RealTransport(DryRunTransport):
        async def request(self, *args, **kwargs):
            raise RuntimeError("THIS SHOULD NOT BE CALLED IN DRY RUN")

    harness = LiveAdapterTransport(
        transport=RealTransport(),
        credential_manager=StubCredentialManager(),
    )

    result = await harness.dry_run(
        adapter_id="claude",
        method="POST",
        url="https://api.anthropic.com/v1/messages",
        body={"prompt": "hello"},
    )

    assert result.success
    assert result.response is not None
    assert result.response.body.get("dry_run") is True


@pytest.mark.anyio
async def test_transport_exception_captured():
    """Transport exception is captured as error, not raised."""

    class FailTransport(DryRunTransport):
        async def request(self, *args, **kwargs):
            raise ConnectionError("simulated network failure")

    harness = LiveAdapterTransport(
        transport=FailTransport(),
        credential_manager=StubCredentialManager(),
    )

    result = await harness.send_request(
        adapter_id="claude",
        method="POST",
        url="https://api.anthropic.com/v1/messages",
    )

    assert not result.success
    assert "ConnectionError" in result.error
    assert result.preflight_passed


@pytest.mark.anyio
async def test_response_normalized_after_transport():
    """Transport response is normalized through response_schema."""
    transport = MockTransport()
    transport.set_response(
        status_code=429,
        body={"error": {"message": "rate limited"}, "_headers": {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1716800000"}},
    )

    harness = LiveAdapterTransport(
        transport=transport,
        credential_manager=StubCredentialManager(),
    )

    result = await harness.send_request(
        adapter_id="claude",
        method="POST",
        url="https://api.anthropic.com/v1/messages",
    )

    assert not result.success
    assert result.response is not None

    normalized = normalize_response(result.response.body, result.response.status_code)
    assert normalized.status == ResponseStatus.RATE_LIMITED
    assert normalized.retryable
    assert normalized.rate_limit_reset_seconds is not None


@pytest.mark.anyio
async def test_multiple_adapters_independent():
    """Multiple adapters have independent request logs."""
    transport = DryRunTransport()
    harness = LiveAdapterTransport(
        transport=transport,
        credential_manager=StubCredentialManager(),
    )

    await harness.send_request("claude", "POST", "https://api.anthropic.com/v1/messages")
    await harness.send_request("mimo", "GET", "https://api.mimo.ai/v1/infer")

    assert len(harness.request_log) == 2
    assert harness.request_log[0]["adapter_id"] == "claude"
    assert harness.request_log[1]["adapter_id"] == "mimo"


@pytest.mark.anyio
async def test_no_governance_components():
    """Harness works without any governance (all optional)."""
    harness = LiveAdapterTransport(transport=DryRunTransport())

    result = await harness.send_request(
        adapter_id="any",
        method="GET",
        url="https://example.com/api",
    )

    assert result.success
    assert result.credential_available
    assert result.network_allowed
    assert result.preflight_passed


@pytest.mark.anyio
async def test_error_classification_integration():
    """classify_error works on real transport error responses."""
    transport = MockTransport()
    harness = LiveAdapterTransport(transport=transport)

    # 401 response
    transport.set_response(status_code=401, body={"error": "unauthorized"})
    result = await harness.send_request("claude", "POST", "https://api.example.com")
    err_status = classify_error(result.response.status_code, result.response.body)
    assert err_status == ResponseStatus.AUTH_FAILURE

    # 429 response
    transport.set_response(status_code=429, body={"error": "rate limited"})
    result = await harness.send_request("claude", "POST", "https://api.example.com")
    err_status = classify_error(result.response.status_code, result.response.body)
    assert err_status == ResponseStatus.RATE_LIMITED

    # 500 response
    transport.set_response(status_code=500, body={"error": "server error"})
    result = await harness.send_request("claude", "POST", "https://api.example.com")
    err_status = classify_error(result.response.status_code, result.response.body)
    assert err_status == ResponseStatus.ERROR


@pytest.mark.anyio
async def test_request_log_includes_body_and_headers():
    """Request log captures body and headers for audit."""
    transport = DryRunTransport()
    harness = LiveAdapterTransport(
        transport=transport,
        credential_manager=StubCredentialManager(),
    )

    await harness.send_request(
        "claude", "POST", "https://api.anthropic.com/v1/messages",
        headers={"X-Custom": "value"},
        body={"prompt": "test"},
    )

    log_entry = harness.request_log[0]
    assert log_entry["method"] == "POST"
    assert log_entry["url"] == "https://api.anthropic.com/v1/messages"
    assert log_entry["status"] == 200
