"""Request signing dry-run. Signs requests without real credentials."""
from __future__ import annotations
import json, hashlib, pathlib, uuid
from dataclasses import dataclass

@dataclass(frozen=True)
class SigningResult:
    signing_mode: str
    fake_signature: bool
    signature_redacted: bool
    real_secret_used: bool
    request_sendable: bool
    network_called: bool
    def to_dict(self) -> dict:
        return {"signing_mode": self.signing_mode, "fake_signature": self.fake_signature, "signature_redacted": self.signature_redacted, "real_secret_used": self.real_secret_used, "request_sendable": self.request_sendable, "network_called": self.network_called}

def build_unsigned_envelope(symbol: str, side: str, quantity: float) -> dict:
    return {"symbol": symbol, "side": side, "quantity": quantity, "timestamp": "2026-01-01T00:00:00Z", "recvWindow": 5000}

def simulate_canonical_string(envelope: dict) -> str:
    parts = [f"{k}={v}" for k, v in sorted(envelope.items())]
    return "&".join(parts)

def produce_fake_signature(canonical: str) -> str:
    return hashlib.sha256(f"FAKE_SECRET_{canonical}".encode()).hexdigest()

def run_signing_dry_run(symbol: str, side: str, quantity: float) -> SigningResult:
    envelope = build_unsigned_envelope(symbol, side, quantity)
    canonical = simulate_canonical_string(envelope)
    sig = produce_fake_signature(canonical)
    return SigningResult(
        signing_mode="DRY_RUN_ONLY", fake_signature=True, signature_redacted=True,
        real_secret_used=False, request_sendable=False, network_called=False,
    )

def write_result(result: SigningResult, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

def render_report(result: SigningResult) -> str:
    lines = ["# Request Signing Dry-Run Report", "", "## Status", ""]
    for k, v in result.to_dict().items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Conclusion", "", "REQUEST_SIGNING_DRY_RUN_VALID", ""])
    return "\n".join(lines)
