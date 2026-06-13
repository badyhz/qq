"""Exchange sandbox adapter stub. Defines boundaries without network access."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass

@dataclass(frozen=True)
class AdapterStubResult:
    stub_only: bool
    network_called: bool
    real_submit: bool
    testnet_submit: bool
    no_submit_enforced: bool
    method: str
    detail: str
    def to_dict(self) -> dict:
        return {"stub_only": self.stub_only, "network_called": self.network_called, "real_submit": self.real_submit, "testnet_submit": self.testnet_submit, "no_submit_enforced": self.no_submit_enforced, "method": self.method, "detail": self.detail}

STUB_PROFILE = {"exchange": "binance_testnet", "base_url": "https://testnet.binance.vision", "api_key": "***STUB_REDACTED***", "api_secret": "***STUB_REDACTED***"}

def load_connection_profile_stub() -> AdapterStubResult:
    return AdapterStubResult(True, False, False, False, True, "load_connection_profile_stub", "stub profile loaded, no real connection")

def validate_permissions_stub() -> AdapterStubResult:
    return AdapterStubResult(True, False, False, False, True, "validate_permissions_stub", "stub permissions validated, no real API call")

def build_signed_request_stub() -> AdapterStubResult:
    return AdapterStubResult(True, False, False, False, True, "build_signed_request_stub", "stub signature built, no real signing")

def simulate_network_submit(symbol: str, side: str, quantity: float) -> AdapterStubResult:
    return AdapterStubResult(True, False, False, False, True, "simulate_network_submit", f"simulated {side} {quantity} {symbol}, no network call")

def simulate_network_cancel(order_id: str) -> AdapterStubResult:
    return AdapterStubResult(True, False, False, False, True, "simulate_network_cancel", f"simulated cancel {order_id}, no network call")

def simulate_fetch_order_status(order_id: str) -> AdapterStubResult:
    return AdapterStubResult(True, False, False, False, True, "simulate_fetch_order_status", f"simulated status for {order_id}, no network call")

def simulate_fetch_balance() -> AdapterStubResult:
    return AdapterStubResult(True, False, False, False, True, "simulate_fetch_balance", "simulated balance fetch, no network call")

def simulate_fetch_positions() -> AdapterStubResult:
    return AdapterStubResult(True, False, False, False, True, "simulate_fetch_positions", "simulated positions fetch, no network call")

def run_all_stubs() -> list[AdapterStubResult]:
    return [
        load_connection_profile_stub(),
        validate_permissions_stub(),
        build_signed_request_stub(),
        simulate_network_submit("BTCUSDT", "BUY", 0.001),
        simulate_network_cancel("SIM_ORD_001"),
        simulate_fetch_order_status("SIM_ORD_001"),
        simulate_fetch_balance(),
        simulate_fetch_positions(),
    ]

def write_results(results: list[AdapterStubResult], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in results], indent=2), encoding="utf-8")
