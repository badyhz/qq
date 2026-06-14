"""Replay scenario matrix."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ReplayScenario:
    scenario_id: str
    category: str
    description: str
    method: str
    path: str
    body: str
    fixture_name: str
    status_code: int
    response_body: dict
    expected_decision: str
    def to_dict(self) -> dict:
        return {"scenario_id": self.scenario_id, "category": self.category, "description": self.description, "method": self.method, "path": self.path, "body": self.body, "fixture_name": self.fixture_name, "status_code": self.status_code, "response_body": self.response_body, "expected_decision": self.expected_decision}

SCENARIOS = (
    ReplayScenario("submit_accepted", "submit", "Order accepted by mock exchange", "POST", "/api/v3/order", '{"symbol":"BTCUSDT","side":"BUY","type":"LIMIT","quantity":"0.001","price":"50000"}', "order_accepted", 200, {"orderId": "MOCK_001", "status": "NEW"}, "MOCK_ACCEPTED"),
    ReplayScenario("submit_rejected", "submit", "Order rejected (insufficient balance)", "POST", "/api/v3/order", '{"symbol":"BTCUSDT","side":"BUY","type":"LIMIT","quantity":"100","price":"50000"}', "order_rejected", 400, {"code": -2010, "msg": "Insufficient balance"}, "MOCK_REJECTED"),
    ReplayScenario("cancel_accepted", "cancel", "Cancel accepted by mock exchange", "DELETE", "/api/v3/order", '{"symbol":"BTCUSDT","orderId":"MOCK_001"}', "cancel_success", 200, {"orderId": "MOCK_001", "status": "CANCELED"}, "MOCK_ACCEPTED"),
    ReplayScenario("cancel_rejected", "cancel", "Cancel rejected (unknown order)", "DELETE", "/api/v3/order", '{"symbol":"BTCUSDT","orderId":"UNKNOWN"}', "cancel_rejected", 400, {"code": -2011, "msg": "Unknown order"}, "MOCK_REJECTED"),
    ReplayScenario("auth_failure", "error", "Authentication failed", "GET", "/api/v3/account", "", "auth_failure", 401, {"code": -2008, "msg": "Invalid API-key"}, "BLOCKED"),
    ReplayScenario("permission_denied", "error", "Permission denied", "POST", "/api/v3/order", '{"symbol":"BTCUSDT"}', "permission_denied", 403, {"code": -2015, "msg": "Permission denied"}, "BLOCKED"),
    ReplayScenario("timestamp_drift", "error", "Timestamp drift detected", "GET", "/api/v3/account", "", "timestamp_drift", 400, {"code": -1021, "msg": "Timestamp ahead"}, "BLOCKED"),
    ReplayScenario("rate_limited", "error", "Rate limit exceeded", "GET", "/api/v3/account", "", "rate_limited", 429, {"code": -1003, "msg": "Too much request"}, "BLOCKED"),
    ReplayScenario("malformed_response", "error", "Malformed response from server", "GET", "/api/v3/account", "", "malformed_payload", 500, {"error": "internal_server_error"}, "BLOCKED"),
    ReplayScenario("vault_placeholder_only", "governance", "Vault returns placeholder credentials only", "GET", "/api/v3/account", "", "balance_mock", 200, {"balances": []}, "NOT_READY"),
    ReplayScenario("signing_dummy_only", "governance", "Signing uses dummy fixture only", "POST", "/api/v3/order", '{"symbol":"BTCUSDT"}', "order_accepted", 200, {"orderId": "MOCK_001"}, "NOT_READY"),
    ReplayScenario("governance_blocker", "governance", "Governance blocker present", "POST", "/api/v3/order", '{"symbol":"BTCUSDT"}', "order_accepted", 200, {"orderId": "MOCK_001"}, "DENY"),
    ReplayScenario("unlock_denied", "governance", "Unlock request denied", "POST", "/api/v3/unlock", '{"gate":"submit"}', "permission_denied", 403, {"code": -2015, "msg": "Unlock denied"}, "DENY"),
)

def get_scenarios() -> tuple[ReplayScenario, ...]:
    return SCENARIOS

def write_scenarios(scenarios: tuple[ReplayScenario, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([s.to_dict() for s in scenarios], indent=2), encoding="utf-8")

def render_report(scenarios: tuple[ReplayScenario, ...]) -> str:
    lines = ["# Replay Scenario Matrix", "",
        "**scenario_mode=MOCK_ONLY**", "",
        "| Scenario | Category | Expected Decision |",
        "|----------|----------|-------------------|"]
    for s in scenarios:
        lines.append(f"| {s.scenario_id} | {s.category} | {s.expected_decision} |")
    lines.extend(["", "## Conclusion", "", "MOCK_REPLAY_SCENARIO_MATRIX_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
