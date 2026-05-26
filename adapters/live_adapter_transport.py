"""Adapter Transport Harness — bridges HTTP transport with governance components."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# ── transport protocol (replaces missing class-based HTTPTransport) ──────

class TransportResponse(Protocol):
    status_code: int
    body: dict[str, Any]
    headers: dict[str, str]


class HTTPTransport(Protocol):
    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> TransportResponse: ...


@dataclass
class DryRunTransportResponse:
    status_code: int = 200
    body: dict[str, Any] = field(default_factory=lambda: {"dry_run": True})
    headers: dict[str, str] = field(default_factory=dict)


class DryRunTransport:
    """Stub transport that never sends real requests."""

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> DryRunTransportResponse:
        logger.info(
            "dry_run request: %s %s (headers=%s, body=%s)",
            method, url, headers, body,
        )
        return DryRunTransportResponse()


# ── result dataclass ────────────────────────────────────────────────────

@dataclass
class TransportResult:
    success: bool
    response: TransportResponse | None = None
    error: str | None = None
    preflight_passed: bool = False
    network_allowed: bool = False
    credential_available: bool = False


# ── main harness ────────────────────────────────────────────────────────

class LiveAdapterTransport:
    """Bridges HTTP transport with governance stack.

    Order of checks: credential -> network -> preflight -> send.
    """

    def __init__(
        self,
        transport: HTTPTransport,
        credential_manager=None,
        network_sandbox=None,
        preflight_validator=None,
    ) -> None:
        self._transport = transport
        self._credential_manager = credential_manager
        self._network_sandbox = network_sandbox
        self._preflight_validator = preflight_validator
        self._request_log: list[dict[str, Any]] = []

    # ── internal helpers ────────────────────────────────────────────

    def _log_request(self, adapter_id: str, method: str, url: str, **kw: Any) -> None:
        self._request_log.append({
            "adapter_id": adapter_id,
            "method": method,
            "url": url,
            **kw,
        })

    def prepare_headers(
        self, adapter_id: str, extra_headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        headers: dict[str, str] = dict(extra_headers or {})
        if self._credential_manager is not None:
            cred = self._credential_manager.get_credential(adapter_id)
            if cred is not None:
                headers["Authorization"] = f"Bearer {cred}"
        return headers

    def check_network_policy(self, url: str) -> bool:
        if self._network_sandbox is None:
            return True
        return self._network_sandbox.is_allowed(url)

    def run_preflight(self, adapter_id: str) -> bool:
        if self._preflight_validator is None:
            return True
        result = self._preflight_validator.validate(adapter_id)
        return result.status.value != "fail"

    # ── public API ──────────────────────────────────────────────────

    async def send_request(
        self,
        adapter_id: str,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> TransportResult:
        # 1. credential check
        cred_available = True
        if self._credential_manager is not None:
            cred_available = self._credential_manager.has_credential(adapter_id)
            if not cred_available:
                err = f"missing credential for adapter '{adapter_id}'"
                logger.warning(err)
                self._log_request(adapter_id, method, url, error=err)
                return TransportResult(
                    success=False, error=err,
                    preflight_passed=False, network_allowed=False,
                    credential_available=False,
                )

        # 2. network check
        network_ok = self.check_network_policy(url)
        if not network_ok:
            err = f"network policy blocked URL '{url}'"
            logger.warning(err)
            self._log_request(adapter_id, method, url, error=err)
            return TransportResult(
                success=False, error=err,
                preflight_passed=False, network_allowed=False,
                credential_available=cred_available,
            )

        # 3. preflight check
        preflight_ok = self.run_preflight(adapter_id)
        if not preflight_ok:
            err = f"preflight failed for adapter '{adapter_id}'"
            logger.warning(err)
            self._log_request(adapter_id, method, url, error=err)
            return TransportResult(
                success=False, error=err,
                preflight_passed=False, network_allowed=True,
                credential_available=cred_available,
            )

        # 4. build headers & send
        merged_headers = self.prepare_headers(adapter_id, headers)
        try:
            response = await self._transport.request(method, url, merged_headers, body)
            self._log_request(adapter_id, method, url, status=response.status_code)
            return TransportResult(
                success=200 <= response.status_code < 300,
                response=response,
                preflight_passed=True,
                network_allowed=True,
                credential_available=cred_available,
            )
        except Exception as exc:
            err = f"transport error: {exc.__class__.__name__}: {exc}"
            logger.error(err)
            self._log_request(adapter_id, method, url, error=err)
            return TransportResult(
                success=False, error=err,
                preflight_passed=True, network_allowed=True,
                credential_available=cred_available,
            )

    async def dry_run(
        self,
        adapter_id: str,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> TransportResult:
        """Simulate without sending — uses DryRunTransport internally."""
        original = self._transport
        self._transport = DryRunTransport()  # type: ignore[assignment]
        try:
            return await self.send_request(adapter_id, method, url, headers, body)
        finally:
            self._transport = original

    # ── introspection ───────────────────────────────────────────────

    @property
    def request_log(self) -> list[dict[str, Any]]:
        return list(self._request_log)
