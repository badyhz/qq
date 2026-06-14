"""Mock transport contract for external testnet adapter."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class RequestEnvelope:
    request_id: str
    method: str
    path: str
    timestamp: str
    headers: tuple[tuple[str, str], ...]
    body_hash: str
    def to_dict(self) -> dict:
        return {"request_id": self.request_id, "method": self.method, "path": self.path, "timestamp": self.timestamp, "headers": list(self.headers), "body_hash": self.body_hash}

@dataclass(frozen=True)
class MockResponse:
    response_id: str
    request_id: str
    status_code: int
    fixture_name: str
    body: dict
    latency_ms: int
    def to_dict(self) -> dict:
        return {"response_id": self.response_id, "request_id": self.request_id, "status_code": self.status_code, "fixture_name": self.fixture_name, "body": self.body, "latency_ms": self.latency_ms}

FIXTURES = {
    "order_accepted": {"status": 200, "body": {"orderId": "MOCK_001", "status": "NEW", "symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT", "price": "50000.00", "origQty": "0.001", "executedQty": "0.000", "timeInForce": "GTC"}},
    "order_rejected": {"status": 400, "body": {"code": -2010, "msg": "Account has insufficient balance for requested action."}},
    "cancel_success": {"status": 200, "body": {"orderId": "MOCK_001", "status": "CANCELED", "symbol": "BTCUSDT"}},
    "cancel_rejected": {"status": 400, "body": {"code": -2011, "msg": "Unknown order sent."}},
    "balance_mock": {"status": 200, "body": {"balances": [{"asset": "USDT", "free": "10000.00", "locked": "0.00"}, {"asset": "BTC", "free": "0.10000000", "locked": "0.00000000"}]}},
    "position_mock": {"status": 200, "body": {"positions": [{"symbol": "BTCUSDT", "positionAmt": "0.000", "entryPrice": "0.00", "unrealizedProfit": "0.00"}]}},
    "permission_denied": {"status": 403, "body": {"code": -2015, "msg": "Invalid API-key, IP, or permissions for action."}},
    "rate_limited": {"status": 429, "body": {"code": -1003, "msg": "Too much request weight used."}},
    "timestamp_drift": {"status": 400, "body": {"code": -1021, "msg": "Timestamp for this request was 1000ms ahead of the server's time."}},
    "malformed_payload": {"status": 500, "body": {"error": "internal_server_error", "detail": "malformed response"}},
    "auth_failure": {"status": 401, "body": {"code": -2008, "msg": "Invalid API-key, IP, or permissions for action."}},
}

def create_request_envelope(method: str, path: str, body: str = "") -> RequestEnvelope:
    import hashlib
    return RequestEnvelope(
        request_id=f"REQ_{uuid.uuid4().hex[:12]}",
        method=method,
        path=path,
        timestamp=datetime.now(timezone.utc).isoformat(),
        headers=(("Content-Type", "application/json"), ("X-Mock-Transport", "true")),
        body_hash=hashlib.sha256(body.encode()).hexdigest() if body else hashlib.sha256(b"").hexdigest(),
    )

def dispatch_mock(fixture_name: str, request_id: str) -> MockResponse:
    fixture = FIXTURES.get(fixture_name)
    if fixture is None:
        return MockResponse(
            response_id=f"RES_{uuid.uuid4().hex[:12]}",
            request_id=request_id,
            status_code=404,
            fixture_name="unknown",
            body={"error": f"Unknown fixture: {fixture_name}"},
            latency_ms=0,
        )
    return MockResponse(
        response_id=f"RES_{uuid.uuid4().hex[:12]}",
        request_id=request_id,
        status_code=fixture["status"],
        fixture_name=fixture_name,
        body=fixture["body"],
        latency_ms=5,
    )

def get_available_fixtures() -> tuple[str, ...]:
    return tuple(FIXTURES.keys())

def write_contract(data: dict, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")

def render_report() -> str:
    lines = ["# Mock Transport Contract", "",
        "**transport_mode=MOCK_ONLY**",
        "**network_client_implemented=false**",
        "**network_called=false**",
        "**submit_allowed=false**", "",
        "## Available Fixtures", ""]
    for name in FIXTURES:
        lines.append(f"- {name}: status={FIXTURES[name]['status']}")
    lines.extend(["", "## Conclusion", "", "MOCK_TRANSPORT_CONTRACT_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
