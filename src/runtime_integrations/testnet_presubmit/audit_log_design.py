"""Audit log design. Tamper-evident event log for sandbox operations."""
from __future__ import annotations
import json, hashlib, pathlib
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    timestamp: str
    event_type: str
    source: str
    previous_hash: str
    event_hash: str
    no_submit_enforced: bool
    def to_dict(self) -> dict:
        return {"event_id": self.event_id, "timestamp": self.timestamp, "event_type": self.event_type, "source": self.source, "previous_hash": self.previous_hash, "event_hash": self.event_hash, "no_submit_enforced": self.no_submit_enforced}

GENESIS_HASH = "0" * 64

def compute_event_hash(event_id: str, timestamp: str, event_type: str, source: str, previous_hash: str) -> str:
    payload = f"{event_id}|{timestamp}|{event_type}|{source}|{previous_hash}"
    return hashlib.sha256(payload.encode()).hexdigest()

def create_event(event_type: str, source: str, previous_hash: str, event_id: str | None = None) -> AuditEvent:
    now = datetime.now(timezone.utc).isoformat()
    eid = event_id or f"EVT_{event_type}_{now[:19]}"
    h = compute_event_hash(eid, now, event_type, source, previous_hash)
    return AuditEvent(eid, now, event_type, source, previous_hash, h, True)

def build_sample_chain() -> list[AuditEvent]:
    events = []
    prev = GENESIS_HASH
    for etype in ("signal_selected", "submit_intent_built", "risk_checked", "approval_checked", "kill_switch_checked", "simulated_submit", "simulated_cancel", "reconciliation_checked"):
        evt = create_event(etype, "testnet_presubmit", prev)
        events.append(evt)
        prev = evt.event_hash
    return events

def write_events(events: list[AuditEvent], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(e.to_dict()) for e in events) + ("\n" if events else ""), encoding="utf-8")
