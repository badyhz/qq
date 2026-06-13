"""Watchlist loader. Deduplicates and scores watchlist items from research sources."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoredWatchlistEntry:
    ticker: str
    mention_count: int
    sources: tuple[str, ...]
    score: float
    signal_type: str

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "mention_count": self.mention_count,
            "sources": list(self.sources),
            "score": self.score,
            "signal_type": self.signal_type,
        }


def score_watchlist(items: list[dict]) -> list[ScoredWatchlistEntry]:
    """Score and deduplicate watchlist items by ticker."""
    ticker_data: dict[str, dict] = {}
    for item in items:
        ticker = item.get("ticker", "")
        if not ticker:
            continue
        if ticker not in ticker_data:
            ticker_data[ticker] = {"count": 0, "sources": set()}
        ticker_data[ticker]["count"] += 1
        src = item.get("source", "unknown")
        ticker_data[ticker]["sources"].add(src)

    entries = []
    for ticker, data in sorted(ticker_data.items()):
        count = data["count"]
        score = min(1.0, count * 0.2)
        entries.append(ScoredWatchlistEntry(
            ticker=ticker,
            mention_count=count,
            sources=tuple(sorted(data["sources"])),
            score=round(score, 2),
            signal_type="research_mention",
        ))

    return sorted(entries, key=lambda e: e.score, reverse=True)


def load_and_score(evidence_path: pathlib.Path) -> list[ScoredWatchlistEntry]:
    """Load watchlist evidence and produce scored entries."""
    if not evidence_path.exists():
        return []
    items = []
    for line in evidence_path.read_text(encoding="utf-8").strip().splitlines():
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return score_watchlist(items)


def write_scored_watchlist(entries: list[ScoredWatchlistEntry], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([e.to_dict() for e in entries], indent=2),
        encoding="utf-8",
    )
