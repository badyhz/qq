"""Request signing fixture validation."""
from __future__ import annotations
import hashlib, json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class SigningEnvelope:
    envelope_id: str
    method: str
    path: str
    timestamp_ms: int
    nonce: str
    payload_hash: str
    canonical_string: str
    signature: str
    key_id: str
    real_signing: bool
    def to_dict(self) -> dict:
        return {"envelope_id": self.envelope_id, "method": self.method, "path": self.path, "timestamp_ms": self.timestamp_ms, "nonce": self.nonce, "payload_hash": self.payload_hash, "canonical_string": self.canonical_string, "signature": self.signature, "key_id": self.key_id, "real_signing": self.real_signing}

def build_fixture_envelope(method: str, path: str, body: str = "") -> SigningEnvelope:
    import uuid, time
    timestamp_ms = int(time.time() * 1000)
    nonce = str(uuid.uuid4())
    payload_hash = hashlib.sha256(body.encode()).hexdigest() if body else hashlib.sha256(b"").hexdigest()
    canonical = f"{method}\n{path}\n{timestamp_ms}\n{nonce}\n{payload_hash}"
    fake_secret = "MOCK_SECRET_KEY_FOR_TESTING_ONLY"
    signature = hashlib.sha256(f"{canonical}\n{fake_secret}".encode()).hexdigest()
    return SigningEnvelope(
        envelope_id=f"ENV_{uuid.uuid4().hex[:12]}",
        method=method, path=path,
        timestamp_ms=timestamp_ms, nonce=nonce,
        payload_hash=payload_hash, canonical_string=canonical,
        signature=signature, key_id="KEY_READ_****",
        real_signing=False,
    )

def validate_envelope(envelope: dict) -> bool:
    if envelope.get("real_signing") is True:
        return False
    if "MOCK_SECRET" not in str(envelope.get("key_id", "")) and "****" not in str(envelope.get("key_id", "")):
        return False
    if len(envelope.get("signature", "")) < 10:
        return False
    return True

def write_envelope(envelope: SigningEnvelope, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope.to_dict(), indent=2), encoding="utf-8")

def render_report() -> str:
    lines = ["# Request Signing Fixture Validation", "",
        "**signing_mode=FIXTURE_ONLY**",
        "**real_secret_used=false**",
        "**request_sendable=false**",
        "**submit_allowed=false**", "",
        "## Conclusion", "",
        "REQUEST_SIGNING_FIXTURE_VALIDATION_READY",
        "REAL_SIGNING_NOT_ALLOWED",
        "REAL_CREDENTIALS_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""]
    return "\n".join(lines)
