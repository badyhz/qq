"""Exchange response fixture schema."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ResponseFixture:
    fixture_id: str
    category: str  # submit, cancel, reconcile, error
    status_code: int
    description: str
    def to_dict(self) -> dict:
        return {"fixture_id": self.fixture_id, "category": self.category, "status_code": self.status_code, "description": self.description}

FIXTURES = (
    ResponseFixture("submit_success", "submit", 200, "Order accepted by exchange"),
    ResponseFixture("submit_rejected", "submit", 400, "Order rejected (insufficient balance)"),
    ResponseFixture("cancel_success", "cancel", 200, "Order cancelled successfully"),
    ResponseFixture("cancel_rejected", "cancel", 400, "Cancel rejected (unknown order)"),
    ResponseFixture("recon_balance", "reconcile", 200, "Balance snapshot returned"),
    ResponseFixture("recon_position", "reconcile", 200, "Position snapshot returned"),
    ResponseFixture("permission_denied", "error", 403, "API key lacks required permission"),
    ResponseFixture("rate_limited", "error", 429, "Rate limit exceeded"),
    ResponseFixture("timestamp_drift", "error", 400, "Timestamp ahead of server time"),
    ResponseFixture("malformed_payload", "error", 500, "Server returned malformed response"),
    ResponseFixture("auth_failure", "error", 401, "Authentication failed"),
)

def get_fixtures() -> tuple[ResponseFixture, ...]:
    return FIXTURES

def write_fixtures(fixtures: tuple[ResponseFixture, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([f.to_dict() for f in fixtures], indent=2), encoding="utf-8")

def render_report(fixtures: tuple[ResponseFixture, ...]) -> str:
    lines = ["# Exchange Response Fixture Schema", "",
        "**fixture_mode=MOCK_ONLY**",
        "**submit_allowed=false**", "",
        "| Fixture | Category | Status | Description |",
        "|---------|----------|--------|-------------|"]
    for f in fixtures:
        lines.append(f"| {f.fixture_id} | {f.category} | {f.status_code} | {f.description} |")
    lines.extend(["", "## Conclusion", "", "EXCHANGE_RESPONSE_FIXTURE_SCHEMA_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
