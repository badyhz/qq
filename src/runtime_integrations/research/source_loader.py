"""Research source loader. Reads local fixture data and produces watchlist evidence."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class WatchlistItem:
    ticker: str
    source: str
    signal_type: str
    confidence: float
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "source": self.source,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class ResearchSourceStatus:
    source_name: str
    items_loaded: int
    status: str
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "source_name": self.source_name,
            "items_loaded": self.items_loaded,
            "status": self.status,
            "error": self.error,
        }


def load_watchlist_from_jsonl(path: pathlib.Path) -> list[WatchlistItem]:
    """Load watchlist items from a JSONL file."""
    items = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            tickers = obj.get("tickers", [])
            ts = obj.get("timestamp", obj.get("imported_at", ""))
            for ticker in tickers:
                items.append(WatchlistItem(
                    ticker=ticker,
                    source=obj.get("source_file", "unknown"),
                    signal_type="research_mention",
                    confidence=0.5,
                    timestamp=ts,
                ))
        except json.JSONDecodeError:
            continue
    return items


def load_watchlist_from_json(path: pathlib.Path) -> list[WatchlistItem]:
    """Load watchlist items from a JSON array file."""
    items = []
    if not path.exists():
        return items
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for obj in data:
                tickers = obj.get("tickers", [])
                ts = obj.get("timestamp", obj.get("imported_at", ""))
                for ticker in tickers:
                    items.append(WatchlistItem(
                        ticker=ticker,
                        source=obj.get("source_file", "unknown"),
                        signal_type="research_mention",
                        confidence=0.5,
                        timestamp=ts,
                    ))
    except (json.JSONDecodeError, KeyError):
        pass
    return items


def load_all_research_sources(data_dir: pathlib.Path) -> tuple[list[WatchlistItem], list[ResearchSourceStatus]]:
    """Load all research sources from data directory."""
    all_items: list[WatchlistItem] = []
    statuses: list[ResearchSourceStatus] = []

    # Search for x_exports JSONL files
    x_export_dir = data_dir / "x_exports"
    if x_export_dir.exists():
        for p in sorted(x_export_dir.glob("*.jsonl")):
            items = load_watchlist_from_jsonl(p)
            all_items.extend(items)
            statuses.append(ResearchSourceStatus(
                source_name=p.name,
                items_loaded=len(items),
                status="LOADED" if items else "EMPTY",
            ))

    # Search for any other JSON watchlist files
    for p in sorted(data_dir.glob("**/*watchlist*.json")):
        items = load_watchlist_from_json(p)
        all_items.extend(items)
        statuses.append(ResearchSourceStatus(
            source_name=str(p.relative_to(data_dir)),
            items_loaded=len(items),
            status="LOADED" if items else "EMPTY",
        ))

    if not statuses:
        statuses.append(ResearchSourceStatus(
            source_name="no_sources_found",
            items_loaded=0,
            status="NO_SOURCES",
        ))

    return all_items, statuses


def write_watchlist_evidence(items: list[WatchlistItem], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(i.to_dict()) for i in items) + ("\n" if items else ""),
        encoding="utf-8",
    )


def write_source_status(statuses: list[ResearchSourceStatus], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([s.to_dict() for s in statuses], indent=2),
        encoding="utf-8",
    )
