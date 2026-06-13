"""Shadow evidence exporter. Exports promotion evidence from shadow signals."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class PromotionEvidence:
    evidence_id: str
    ticker: str
    signal_type: str
    confidence: float
    direction: str
    shadow_only: bool
    no_submit: bool
    recommendation: str  # PROMOTE, HOLD, REJECT
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "ticker": self.ticker,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "direction": self.direction,
            "shadow_only": self.shadow_only,
            "no_submit": self.no_submit,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
        }


def export_promotion_evidence(signals: list[dict]) -> list[PromotionEvidence]:
    """Export promotion evidence from shadow signals."""
    evidence = []
    now = datetime.now(timezone.utc).isoformat()
    for sig in signals:
        conf = sig.get("confidence", 0.0)
        if conf >= 0.8:
            rec = "PROMOTE"
        elif conf >= 0.4:
            rec = "HOLD"
        else:
            rec = "REJECT"
        evidence.append(PromotionEvidence(
            evidence_id=f"pe_{sig.get('signal_id', 'unknown')}",
            ticker=sig.get("ticker", "UNKNOWN"),
            signal_type=sig.get("signal_type", "unknown"),
            confidence=conf,
            direction=sig.get("direction", "UNKNOWN"),
            shadow_only=True,
            no_submit=True,
            recommendation=rec,
            timestamp=now,
        ))
    return evidence


def write_promotion_evidence(evidence: list[PromotionEvidence], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(e.to_dict()) for e in evidence) + ("\n" if evidence else ""),
        encoding="utf-8",
    )
