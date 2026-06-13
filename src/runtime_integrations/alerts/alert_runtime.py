"""Alert runtime. Loads runtime artifacts and produces alert events."""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AlertEvent:
    alert_id: str
    source: str
    alert_type: str
    severity: str
    title: str
    body: str
    ticker: str | None
    dedup_key: str
    timestamp: str
    dry_run: bool = True

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "source": self.source,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "title": self.title,
            "body": self.body,
            "ticker": self.ticker,
            "dedup_key": self.dedup_key,
            "timestamp": self.timestamp,
            "dry_run": self.dry_run,
        }


def _dedup_key(source: str, alert_type: str, ticker: str | None) -> str:
    raw = f"{source}:{alert_type}:{ticker or 'none'}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_alerts_from_watchlist(evidence_path: pathlib.Path) -> list[AlertEvent]:
    """Generate alerts from watchlist evidence."""
    alerts = []
    if not evidence_path.exists():
        return alerts
    now = datetime.now(timezone.utc).isoformat()
    for line in evidence_path.read_text(encoding="utf-8").strip().splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        ticker = item.get("ticker", "UNKNOWN")
        alerts.append(AlertEvent(
            alert_id=f"alert_research_{ticker}_{len(alerts):04d}",
            source="research",
            alert_type="watchlist_mention",
            severity="INFO",
            title=f"Research mention: {ticker}",
            body=f"Ticker {ticker} found in research sources",
            ticker=ticker,
            dedup_key=_dedup_key("research", "watchlist_mention", ticker),
            timestamp=now,
        ))
    return alerts


def load_alerts_from_signals(signals_path: pathlib.Path) -> list[AlertEvent]:
    """Generate alerts from shadow signals."""
    alerts = []
    if not signals_path.exists():
        return alerts
    now = datetime.now(timezone.utc).isoformat()
    for line in signals_path.read_text(encoding="utf-8").strip().splitlines():
        if not line.strip():
            continue
        try:
            sig = json.loads(line)
        except json.JSONDecodeError:
            continue
        ticker = sig.get("ticker", "UNKNOWN")
        direction = sig.get("direction", "UNKNOWN")
        conf = sig.get("confidence", 0.0)
        severity = "WARNING" if conf >= 0.6 else "INFO"
        alerts.append(AlertEvent(
            alert_id=f"alert_shadow_{len(alerts):04d}",
            source="shadow",
            alert_type="shadow_signal",
            severity=severity,
            title=f"Shadow signal: {direction} {ticker}",
            body=f"Shadow signal {direction} {ticker} confidence={conf}",
            ticker=ticker,
            dedup_key=_dedup_key("shadow", "shadow_signal", ticker),
            timestamp=now,
        ))
    return alerts


def load_alerts_from_testnet(testnet_path: pathlib.Path) -> list[AlertEvent]:
    """Generate alerts from testnet simulation evidence."""
    alerts = []
    if not testnet_path.exists():
        return alerts
    now = datetime.now(timezone.utc).isoformat()
    try:
        data = json.loads(testnet_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return alerts
    if isinstance(data, list):
        for item in data:
            alerts.append(AlertEvent(
                alert_id=f"alert_testnet_{len(alerts):04d}",
                source="testnet_sim",
                alert_type="testnet_simulation",
                severity="INFO",
                title="Testnet simulation completed",
                body=json.dumps(item)[:200],
                ticker=None,
                dedup_key=_dedup_key("testnet_sim", "testnet_simulation", None),
                timestamp=now,
            ))
    return alerts


def deduplicate_alerts(alerts: list[AlertEvent]) -> list[AlertEvent]:
    """Deduplicate alerts by dedup_key, keeping first occurrence."""
    seen: set[str] = set()
    result = []
    for a in alerts:
        if a.dedup_key not in seen:
            seen.add(a.dedup_key)
            result.append(a)
    return result


def write_alerts(alerts: list[AlertEvent], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(a.to_dict()) for a in alerts) + ("\n" if alerts else ""),
        encoding="utf-8",
    )
