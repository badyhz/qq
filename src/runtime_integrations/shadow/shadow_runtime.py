"""Shadow runtime. Runs shadow signal evaluation with fixture data."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ShadowSignal:
    signal_id: str
    ticker: str
    signal_type: str
    direction: str
    confidence: float
    source: str
    timestamp: str
    shadow_only: bool = True
    no_submit: bool = True

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "ticker": self.ticker,
            "signal_type": self.signal_type,
            "direction": self.direction,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp,
            "shadow_only": self.shadow_only,
            "no_submit": self.no_submit,
        }


@dataclass(frozen=True)
class ShadowScorecard:
    run_id: str
    signals_generated: int
    unique_tickers: int
    avg_confidence: float
    top_signal: str | None
    timestamp: str
    shadow_only: bool = True

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "signals_generated": self.signals_generated,
            "unique_tickers": self.unique_tickers,
            "avg_confidence": self.avg_confidence,
            "top_signal": self.top_signal,
            "timestamp": self.timestamp,
            "shadow_only": self.shadow_only,
        }


def generate_signals_from_watchlist(
    watchlist: list[dict],
    run_id: str,
) -> list[ShadowSignal]:
    """Generate shadow signals from scored watchlist entries."""
    signals = []
    now = datetime.now(timezone.utc).isoformat()
    for i, entry in enumerate(watchlist):
        ticker = entry.get("ticker", "UNKNOWN")
        score = entry.get("score", 0.0)
        if score < 0.2:
            continue
        direction = "BUY" if score >= 0.6 else "WATCH"
        signals.append(ShadowSignal(
            signal_id=f"sig_{run_id}_{i:04d}",
            ticker=ticker,
            signal_type="shadow_watchlist",
            direction=direction,
            confidence=score,
            source="research_watchlist",
            timestamp=now,
        ))
    return signals


def build_scorecard(signals: list[ShadowSignal], run_id: str) -> ShadowScorecard:
    """Build scorecard from signals."""
    now = datetime.now(timezone.utc).isoformat()
    if not signals:
        return ShadowScorecard(
            run_id=run_id,
            signals_generated=0,
            unique_tickers=0,
            avg_confidence=0.0,
            top_signal=None,
            timestamp=now,
        )
    tickers = {s.ticker for s in signals}
    confs = [s.confidence for s in signals]
    top = max(signals, key=lambda s: s.confidence)
    return ShadowScorecard(
        run_id=run_id,
        signals_generated=len(signals),
        unique_tickers=len(tickers),
        avg_confidence=round(sum(confs) / len(confs), 3),
        top_signal=top.ticker,
        timestamp=now,
    )


def write_signals(signals: list[ShadowSignal], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(s.to_dict()) for s in signals) + ("\n" if signals else ""),
        encoding="utf-8",
    )


def write_scorecard(scorecard: ShadowScorecard, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(scorecard.to_dict(), indent=2), encoding="utf-8")
