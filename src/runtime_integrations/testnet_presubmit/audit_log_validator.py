"""Audit log validator. Validates hash chain integrity and detects tampering."""
from __future__ import annotations
import json, hashlib, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class AuditValidation:
    total_events: int
    chain_valid: bool
    tampering_detected: bool
    errors: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"total_events": self.total_events, "chain_valid": self.chain_valid, "tampering_detected": self.tampering_detected, "errors": list(self.errors)}

def compute_hash(event_id: str, timestamp: str, event_type: str, source: str, previous_hash: str) -> str:
    payload = f"{event_id}|{timestamp}|{event_type}|{source}|{previous_hash}"
    return hashlib.sha256(payload.encode()).hexdigest()

def validate_chain(events: list[dict]) -> AuditValidation:
    errors = []
    tampering = False
    for i, evt in enumerate(events):
        expected_prev = "0" * 64 if i == 0 else events[i - 1].get("event_hash", "")
        actual_prev = evt.get("previous_hash", "")
        if expected_prev != actual_prev:
            errors.append(f"event {i}: previous_hash mismatch")
            tampering = True
        expected_hash = compute_hash(evt["event_id"], evt["timestamp"], evt["event_type"], evt["source"], actual_prev)
        if expected_hash != evt.get("event_hash", ""):
            errors.append(f"event {i}: event_hash mismatch")
            tampering = True
    return AuditValidation(len(events), len(errors) == 0, tampering, tuple(errors))

def write_validation(val: AuditValidation, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(val.to_dict(), indent=2), encoding="utf-8")
