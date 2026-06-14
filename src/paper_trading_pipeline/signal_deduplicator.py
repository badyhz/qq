"""Signal deduplicator — removes duplicate and cooldown-conflicting signals."""
from __future__ import annotations
import csv, json, pathlib
from datetime import datetime, timedelta
from src.paper_trading_pipeline.models import DedupedSignalBatch, new_id, utc_now_iso

COOLDOWN_MINUTES = 30


def _normalize_time(t: str) -> str:
    """Normalize time string: strip T, microseconds, timezone."""
    if not t:
        return ""
    t = t.split("+")[0].split("Z")[0]
    t = t.replace("T", " ")
    if "." in t:
        t = t.split(".")[0]
    return t.strip()


def _parse_time(t: str) -> datetime | None:
    norm = _normalize_time(t)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(norm, fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def deduplicate_signals(
    signals: list[dict],
    alerts: list[dict] | None = None,
    cooldown_minutes: int = COOLDOWN_MINUTES,
) -> DedupedSignalBatch:
    alerts = alerts or []
    raw_count = len(signals) + len(alerts)
    notes: list[str] = []

    # Build signal-like dicts, prioritizing CSV signals (have price data)
    signal_keys: set[tuple[str, str, str]] = set()
    merged: list[dict] = []
    for s in signals:
        raw_time = s.get("time", s.get("signal_time", ""))
        key = (s.get("symbol", ""), s.get("interval", "5m"), _normalize_time(raw_time))
        signal_keys.add(key)
        merged.append({**s, "_source": "signal"})
    for a in alerts:
        a_time = a.get("signal_time", "")
        a_key = (a.get("symbol", ""), a.get("interval", "5m"), _normalize_time(a_time))
        if a_key in signal_keys:
            continue  # skip alerts that already have a CSV signal with price data
        merged.append({
            "symbol": a.get("symbol", ""),
            "interval": a.get("interval", "5m"),
            "time": a_time,
            "signal_time": a_time,
            "price": 0,  # alerts don't have price
            "signal_level": "B",
            "drop_pct": 0, "volume_ratio": 0, "above_ma99": True,
            "reason": "", "force_alert": a.get("force_alert", False),
            "dry_run": a.get("dry_run", True),
            "_source": "alert",
        })

    # Step 1: exact dedup by symbol+timeframe+normalized_time
    seen: set[tuple[str, str, str]] = set()
    exact_deduped: list[dict] = []
    dup_count = 0
    for s in merged:
        raw_time = s.get("time", s.get("signal_time", ""))
        key = (s.get("symbol", ""), s.get("interval", "5m"), _normalize_time(raw_time))
        if key not in seen:
            seen.add(key)
            exact_deduped.append(s)
        else:
            dup_count += 1

    if dup_count > 0:
        notes.append(f"Removed {dup_count} exact duplicates")

    # Step 2: cooldown filter — keep best per symbol within window
    cooldown_filtered = 0
    by_symbol: dict[str, list[dict]] = {}
    for s in exact_deduped:
        sym = s.get("symbol", "")
        by_symbol.setdefault(sym, []).append(s)

    final: list[dict] = []
    for sym, sigs in by_symbol.items():
        sigs.sort(key=lambda x: x.get("time", x.get("signal_time", "")), reverse=True)
        kept: list[dict] = []
        last_time: datetime | None = None
        for s in sigs:
            t = _parse_time(s.get("time", s.get("signal_time", "")))
            if t and last_time and (last_time - t) < timedelta(minutes=cooldown_minutes):
                cooldown_filtered += 1
                continue
            kept.append(s)
            if t:
                last_time = t
        final.extend(kept)

    if cooldown_filtered > 0:
        notes.append(f"Filtered {cooldown_filtered} signals within {cooldown_minutes}min cooldown")

    force_count = sum(1 for s in final if s.get("force_alert"))
    if force_count > 0:
        notes.append(f"{force_count} force_alert signals preserved")

    return DedupedSignalBatch(
        batch_id=new_id("DSB"),
        created_at=utc_now_iso(),
        raw_count=raw_count,
        deduped_count=len(final),
        duplicate_count=dup_count,
        cooldown_filtered_count=cooldown_filtered,
        force_alert_count=force_count,
        signals=tuple(final),
        dedup_notes=notes,
        final_verdict=f"PAPER_TRADING_SIGNAL_DEDUP_READY|RAW={raw_count}|DEDUPED={len(final)}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
