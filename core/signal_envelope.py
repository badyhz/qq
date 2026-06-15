"""Signal envelope — wraps a trading signal with safety metadata.

Every signal passing through the system must be wrapped in a SignalEnvelope.
Enforces dry_run=True and paper/shadow/dry_run modes only.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


ALLOWED_MODES = frozenset({"paper", "shadow", "dry_run"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_signal_id() -> str:
    return f"sig_{uuid.uuid4().hex[:12]}"


@dataclass
class SignalEnvelope:
    signal_id: str = field(default_factory=_new_signal_id)
    strategy_id: str = ""
    symbol: str = ""
    timeframe: str = "1m"
    side: str = "long"            # long | short
    signal_type: str = "entry"    # entry | exit | adjust
    detected_at: str = field(default_factory=_utc_now_iso)
    entry: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    confidence: float = 0.0      # 0..1
    risk_score: float = 0.0      # 0..1
    metadata: dict = field(default_factory=dict)
    dry_run: bool = True
    mode: str = "paper"

    def __post_init__(self) -> None:
        errors = self.validate()
        if errors:
            raise ValueError(f"SignalEnvelope validation failed: {'; '.join(errors)}")

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.dry_run:
            errors.append("dry_run must be True — live signals are rejected")
        if self.mode not in ALLOWED_MODES:
            errors.append(f"mode must be one of {sorted(ALLOWED_MODES)}, got '{self.mode}'")
        if not self.symbol:
            errors.append("symbol is required")
        if not self.strategy_id:
            errors.append("strategy_id is required")
        if self.side not in ("long", "short"):
            errors.append(f"side must be 'long' or 'short', got '{self.side}'")
        if self.signal_type not in ("entry", "exit", "adjust"):
            errors.append(f"signal_type must be 'entry', 'exit', or 'adjust', got '{self.signal_type}'")
        if self.entry <= 0:
            errors.append("entry must be > 0")
        if self.signal_type == "entry":
            if self.stop_loss <= 0:
                errors.append("stop_loss must be > 0 for entry signals")
            if self.take_profit <= 0:
                errors.append("take_profit must be > 0 for entry signals")
        if not (0.0 <= self.confidence <= 1.0):
            errors.append(f"confidence must be 0..1, got {self.confidence}")
        if not (0.0 <= self.risk_score <= 1.0):
            errors.append(f"risk_score must be 0..1, got {self.risk_score}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "side": self.side,
            "signal_type": self.signal_type,
            "detected_at": self.detected_at,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "metadata": self.metadata,
            "dry_run": self.dry_run,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignalEnvelope:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
