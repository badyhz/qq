"""Network governance module — outbound request policy layer.

Defines allowed/denied domains, rate ceilings, and mode-based gating.
NO real outbound requests are made. This is a policy layer, not a network layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set
from urllib.parse import urlparse


@dataclass
class NetworkCheckResult:
    """Result of a URL policy check."""

    allowed: bool
    reason: str  # "allowed", "denied_by_denylist", "not_in_allowlist", "offline_mode", "simulation_mode", "rate_exceeded"
    domain: str


class NetworkSandbox:
    """Outbound request governance. Modes: simulation, offline, restricted."""

    VALID_MODES = {"simulation", "offline", "restricted"}

    def __init__(self, mode: str = "simulation") -> None:
        if mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode: {mode!r}. Must be one of {self.VALID_MODES}")
        self._mode: str = mode
        self._allowed_domains: Set[str] = {"api.anthropic.com", "api.mimo.example.com"}
        self._denied_domains: Set[str] = set()
        self._rate_ceilings: Dict[str, int] = {}  # domain -> max requests
        self._request_counts: Dict[str, int] = {}  # domain -> current count
        self._default_rate_ceiling: int = 100

    # ── domain allow/deny ──────────────────────────────────────────

    def add_allowed_domain(self, domain: str) -> None:
        self._allowed_domains.add(domain)

    def remove_allowed_domain(self, domain: str) -> None:
        self._allowed_domains.discard(domain)

    def add_denied_domain(self, domain: str) -> None:
        self._denied_domains.add(domain)

    def remove_denied_domain(self, domain: str) -> None:
        self._denied_domains.discard(domain)

    # ── rate ceilings ──────────────────────────────────────────────

    def set_rate_ceiling(self, domain: str, max_requests: int) -> None:
        self._rate_ceilings[domain] = max_requests

    def check_rate_ceiling(self, domain: str, current_count: int) -> bool:
        ceiling = self._rate_ceilings.get(domain, self._default_rate_ceiling)
        return current_count < ceiling

    def record_request(self, domain: str) -> None:
        self._request_counts[domain] = self._request_counts.get(domain, 0) + 1

    # ── mode ───────────────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        if mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode: {mode!r}. Must be one of {self.VALID_MODES}")
        self._mode = mode

    # ── checks ─────────────────────────────────────────────────────

    def _extract_domain(self, url: str) -> str:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port
        if port and port not in (80, 443):
            return f"{host}:{port}"
        return host

    def check_request(self, url: str) -> NetworkCheckResult:
        domain = self._extract_domain(url)

        if self._mode == "offline":
            return NetworkCheckResult(allowed=False, reason="offline_mode", domain=domain)

        if self._mode == "simulation":
            # simulation mode: allowed but logged, no real network
            return NetworkCheckResult(allowed=True, reason="simulation_mode", domain=domain)

        # restricted mode
        if domain in self._denied_domains:
            return NetworkCheckResult(allowed=False, reason="denied_by_denylist", domain=domain)

        if domain not in self._allowed_domains:
            return NetworkCheckResult(allowed=False, reason="not_in_allowlist", domain=domain)

        # check rate ceiling
        count = self._request_counts.get(domain, 0)
        ceiling = self._rate_ceilings.get(domain, self._default_rate_ceiling)
        if count >= ceiling:
            return NetworkCheckResult(allowed=False, reason="rate_exceeded", domain=domain)

        return NetworkCheckResult(allowed=True, reason="allowed", domain=domain)

    def is_allowed(self, url: str) -> bool:
        return self.check_request(url).allowed

    # ── summary ────────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "mode": self._mode,
            "allowed_domains": sorted(self._allowed_domains),
            "denied_domains": sorted(self._denied_domains),
            "rate_ceilings": dict(self._rate_ceilings),
            "default_rate_ceiling": self._default_rate_ceiling,
            "request_counts": dict(self._request_counts),
        }
