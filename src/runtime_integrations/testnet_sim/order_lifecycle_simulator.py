"""Testnet order lifecycle simulator. Simulates order lifecycle without real exchange."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    ticker: str
    direction: str
    order_type: str
    quantity: float
    price: float | None
    confidence: float
    timestamp: str
    dry_run: bool = True
    no_submit: bool = True

    def to_dict(self) -> dict:
        return {
            "intent_id": self.intent_id,
            "ticker": self.ticker,
            "direction": self.direction,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "price": self.price,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "dry_run": self.dry_run,
            "no_submit": self.no_submit,
        }


@dataclass(frozen=True)
class LifecycleEvent:
    event_id: str
    intent_id: str
    stage: str
    simulated_response: str
    simulated_fill_price: float | None
    simulated_slippage_bps: float
    simulated_latency_ms: float
    risk_precheck_passed: bool
    no_submit_evidence: bool
    dry_run: bool
    no_real_action: bool
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "intent_id": self.intent_id,
            "stage": self.stage,
            "simulated_response": self.simulated_response,
            "simulated_fill_price": self.simulated_fill_price,
            "simulated_slippage_bps": self.simulated_slippage_bps,
            "simulated_latency_ms": self.simulated_latency_ms,
            "risk_precheck_passed": self.risk_precheck_passed,
            "no_submit_evidence": self.no_submit_evidence,
            "dry_run": self.dry_run,
            "no_real_action": self.no_real_action,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class NoSubmitEvidence:
    evidence_type: str
    dry_run: bool
    events_count: int
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "evidence_type": self.evidence_type,
            "dry_run": self.dry_run,
            "events_count": self.events_count,
            "timestamp": self.timestamp,
        }


def generate_order_intents(signals: list[dict]) -> list[OrderIntent]:
    """Convert shadow signals to simulated order intents."""
    intents = []
    now = datetime.now(timezone.utc).isoformat()
    for sig in signals:
        if sig.get("direction") not in ("BUY", "SELL"):
            continue
        if sig.get("confidence", 0) < 0.5:
            continue
        intents.append(OrderIntent(
            intent_id=f"intent_{sig.get('ticker', 'UNK')}_{sig.get('direction', 'BUY')}_{now}",
            ticker=sig.get("ticker", "UNKNOWN"),
            direction=sig.get("direction", "BUY"),
            order_type="LIMIT",
            quantity=1.0,
            price=None,
            confidence=sig.get("confidence", 0.0),
            timestamp=now,
        ))
    return intents


def simulate_lifecycle(intents: list[OrderIntent]) -> tuple[list[LifecycleEvent], list[NoSubmitEvidence]]:
    """Simulate order lifecycle for each intent."""
    events = []
    now = datetime.now(timezone.utc).isoformat()
    for intent in intents:
        events.append(LifecycleEvent(
            event_id=f"evt_{intent.intent_id}_filled",
            intent_id=intent.intent_id,
            stage="SIMULATED_FILL",
            simulated_response="simulated_fill_successful",
            simulated_fill_price=50000.0 if "BTC" in intent.ticker else 3000.0,
            simulated_slippage_bps=2.5,
            simulated_latency_ms=45.0,
            risk_precheck_passed=True,
            no_submit_evidence=True,
            dry_run=True,
            no_real_action=True,
            timestamp=now,
        ))

    evidence = [
        NoSubmitEvidence(
            evidence_type="no_real_submit",
            dry_run=True,
            events_count=len(events),
            timestamp=now,
        ),
        NoSubmitEvidence(
            evidence_type="no_real_exchange_call",
            dry_run=True,
            events_count=0,
            timestamp=now,
        ),
        NoSubmitEvidence(
            evidence_type="no_real_api_key_read",
            dry_run=True,
            events_count=0,
            timestamp=now,
        ),
    ]

    return events, evidence


def write_intents(intents: list[OrderIntent], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(i.to_dict()) for i in intents) + ("\n" if intents else ""),
        encoding="utf-8",
    )


def write_lifecycle(events: list[LifecycleEvent], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([e.to_dict() for e in events], indent=2),
        encoding="utf-8",
    )


def write_no_submit_evidence(evidence: list[NoSubmitEvidence], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([e.to_dict() for e in evidence], indent=2),
        encoding="utf-8",
    )
