"""Endpoint allowlist stub: defines permitted and blocked endpoints for read-only phase."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class EndpointEntry:
    endpoint_id: str
    url_pattern: str
    category: str
    allowed: bool
    reason: str
    def to_dict(self) -> dict:
        return {"endpoint_id": self.endpoint_id, "url_pattern": self.url_pattern,
                "category": self.category, "allowed": self.allowed, "reason": self.reason}


@dataclass(frozen=True)
class EndpointAllowlistStub:
    stub_id: str
    created_at: str
    entries: tuple[EndpointEntry, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"stub_id": self.stub_id, "created_at": self.created_at,
                "entries": [e.to_dict() for e in self.entries],
                "final_verdict": self.final_verdict}


ENTRIES = (
    EndpointEntry("EP_001", "REAL_EXCHANGE:/api/v3/klines", "MARKET_DATA", False, "Real endpoint blocked in read-only phase"),
    EndpointEntry("EP_002", "REAL_EXCHANGE:/api/v3/ticker/price", "MARKET_DATA", False, "Real endpoint blocked in read-only phase"),
    EndpointEntry("EP_003", "REAL_EXCHANGE:/api/v3/order", "ORDER", False, "Real endpoint blocked in read-only phase"),
    EndpointEntry("EP_004", "REAL_EXCHANGE:/api/v3/account", "ACCOUNT", False, "Real endpoint blocked in read-only phase"),
    EndpointEntry("EP_005", "TESTNET_EXCHANGE:/api/v3/klines", "TESTNET_DATA", False, "Testnet blocked — no real network"),
    EndpointEntry("EP_006", "mock://localhost/fixture/klines", "MOCK_DATA", True, "Mock endpoint allowed for dry-run"),
    EndpointEntry("EP_007", "mock://localhost/fixture/ticker", "MOCK_DATA", True, "Mock endpoint allowed for dry-run"),
    EndpointEntry("EP_008", "mock://localhost/fixture/order", "MOCK_ORDER", True, "Mock endpoint allowed for dry-run"),
    EndpointEntry("EP_009", "file://data/fixtures/klines.csv", "LOCAL_FIXTURE", True, "Local fixture allowed"),
    EndpointEntry("EP_010", "file://data/fixtures/orders.json", "LOCAL_FIXTURE", True, "Local fixture allowed"),
)


def create_stub() -> EndpointAllowlistStub:
    return EndpointAllowlistStub(
        stub_id=f"EAS_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        entries=ENTRIES,
        final_verdict="ENDPOINT_ALLOWLIST_STUB_READY|REAL_ENDPOINTS_BLOCKED|MOCK_ENDPOINTS_ALLOWED|REAL_NETWORK_NOT_ALLOWED",
    )


def write_stub(stub: EndpointAllowlistStub, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stub.to_dict(), indent=2), encoding="utf-8")


def render_report(stub: EndpointAllowlistStub) -> str:
    lines = ["# Endpoint Allowlist Stub", "",
        f"**stub_id={stub.stub_id}**",
        f"**verdict={stub.final_verdict}**", "",
        "## Entries", "",
        "| Endpoint | URL Pattern | Category | Allowed | Reason |",
        "|----------|-------------|----------|:---:|--------|"]
    for e in stub.entries:
        lines.append(f"| {e.endpoint_id} | {e.url_pattern} | {e.category} | {'Y' if e.allowed else 'N'} | {e.reason} |")
    allowed = sum(1 for e in stub.entries if e.allowed)
    blocked = sum(1 for e in stub.entries if not e.allowed)
    lines.extend(["", f"**Allowed: {allowed} | Blocked: {blocked}**", "",
        "## Conclusion", "",
        "ENDPOINT_ALLOWLIST_STUB_READY",
        "REAL_ENDPOINTS_BLOCKED",
        "MOCK_ENDPOINTS_ALLOWED",
        "REAL_NETWORK_NOT_ALLOWED", ""])
    return "\n".join(lines)
