"""T19501 — Unified Alert Center.

Pure deterministic. No I/O. No network. No real notifications.
Defines alert event schema, source registry, dedup, priority classification,
routing, and feishu formatting. All dry-run.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_PRIORITIES: tuple[str, ...] = (
    "INFO",
    "WATCH",
    "IMPORTANT",
    "CRITICAL",
)

VALID_SOURCES: tuple[str, ...] = (
    "earnings",
    "stock_price",
    "macd_rebound",
    "binance_futures",
    "strategy_registry",
    "system_heartbeat",
    "force_alert",
    "manual_test",
)

FORBIDDEN_ACTIONS: tuple[str, ...] = (
    "SEND_REAL_NOTIFICATION",
    "SEND_WEBHOOK",
    "SEND_EMAIL",
    "SEND_SMS",
    "EXECUTE_TRADE",
    "SUBMIT_ORDER",
)


@dataclass(frozen=True)
class AlertEvent:
    """Single alert event."""
    alert_id: str
    source: str
    priority: str
    title: str
    message: str
    ticker: str
    timestamp: str
    dedup_key: str
    is_duplicate: bool
    routed: bool
    route_target: str
    feishu_formatted: bool
    dry_run: bool
    no_real_notification: bool

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "source": self.source,
            "priority": self.priority,
            "title": self.title,
            "message": self.message,
            "ticker": self.ticker,
            "timestamp": self.timestamp,
            "dedup_key": self.dedup_key,
            "is_duplicate": self.is_duplicate,
            "routed": self.routed,
            "route_target": self.route_target,
            "feishu_formatted": self.feishu_formatted,
            "dry_run": self.dry_run,
            "no_real_notification": self.no_real_notification,
        }


@dataclass(frozen=True)
class HeartbeatRecord:
    """System heartbeat record."""
    heartbeat_id: str
    timestamp: str
    status: str
    active_sources: list[str]
    alert_count: int
    duplicate_count: int
    dry_run: bool

    def to_dict(self) -> dict:
        return {
            "heartbeat_id": self.heartbeat_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "active_sources": self.active_sources,
            "alert_count": self.alert_count,
            "duplicate_count": self.duplicate_count,
            "dry_run": self.dry_run,
        }


def _make_dedup_key(source: str, ticker: str, title: str) -> str:
    """Generate dedup key for alert."""
    raw = f"{source}:{ticker}:{title}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def build_alert_event(
    source: str,
    priority: str,
    title: str,
    message: str,
    ticker: str = "",
    timestamp: str = "",
    existing_keys: set[str] | None = None,
) -> AlertEvent:
    """Build a single alert event with dedup check."""
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()

    dedup_key = _make_dedup_key(source, ticker, title)
    is_dup = existing_keys is not None and dedup_key in existing_keys

    return AlertEvent(
        alert_id=f"alert_{dedup_key}",
        source=source,
        priority=priority,
        title=title,
        message=message,
        ticker=ticker,
        timestamp=timestamp,
        dedup_key=dedup_key,
        is_duplicate=is_dup,
        routed=not is_dup,
        route_target="dry_run_log" if not is_dup else "dedup_filtered",
        feishu_formatted=not is_dup,
        dry_run=True,
        no_real_notification=True,
    )


def classify_priority(source: str, raw_priority: str = "") -> str:
    """Classify alert priority based on source and raw signal."""
    if raw_priority in VALID_PRIORITIES:
        return raw_priority

    priority_map = {
        "earnings": "IMPORTANT",
        "stock_price": "WATCH",
        "macd_rebound": "WATCH",
        "binance_futures": "IMPORTANT",
        "strategy_registry": "INFO",
        "system_heartbeat": "INFO",
        "force_alert": "CRITICAL",
        "manual_test": "INFO",
    }
    return priority_map.get(source, "INFO")


def deduplicate_alerts(alerts: list[AlertEvent]) -> list[AlertEvent]:
    """Filter duplicate alerts, keeping first occurrence."""
    seen: set[str] = set()
    result: list[AlertEvent] = []
    for alert in alerts:
        if alert.dedup_key not in seen:
            seen.add(alert.dedup_key)
            result.append(alert)
    return result


def format_feishu(alert: AlertEvent) -> dict:
    """Format alert for Feishu notification (dry-run)."""
    priority_emoji = {
        "INFO": "ℹ️",
        "WATCH": "👁️",
        "IMPORTANT": "⚠️",
        "CRITICAL": "🚨",
    }
    emoji = priority_emoji.get(alert.priority, "📢")

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"{emoji} [{alert.priority}] {alert.title}"},
                "template": "blue" if alert.priority == "INFO" else "orange" if alert.priority in ("WATCH", "IMPORTANT") else "red",
            },
            "elements": [
                {"tag": "div", "text": {"tag": "plain_text", "content": f"Source: {alert.source}"}},
                {"tag": "div", "text": {"tag": "plain_text", "content": f"Ticker: {alert.ticker or 'N/A'}"}},
                {"tag": "div", "text": {"tag": "plain_text", "content": f"Message: {alert.message}"}},
                {"tag": "div", "text": {"tag": "plain_text", "content": f"Time: {alert.timestamp}"}},
                {"tag": "hr"},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": "DRY RUN - No real notification sent"}]},
            ],
        },
        "_dry_run": True,
        "_no_real_notification": True,
    }


def build_heartbeat(
    active_sources: list[str],
    alert_count: int,
    duplicate_count: int,
) -> HeartbeatRecord:
    """Build a system heartbeat record."""
    return HeartbeatRecord(
        heartbeat_id=f"heartbeat_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        status="ALIVE",
        active_sources=active_sources,
        alert_count=alert_count,
        duplicate_count=duplicate_count,
        dry_run=True,
    )


def build_alert_center_status(
    alerts: list[AlertEvent],
    heartbeat: HeartbeatRecord,
) -> dict:
    """Build alert center status summary."""
    priority_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for a in alerts:
        priority_counts[a.priority] = priority_counts.get(a.priority, 0) + 1
        source_counts[a.source] = source_counts.get(a.source, 0) + 1

    return {
        "total_alerts": len(alerts),
        "unique_alerts": sum(1 for a in alerts if not a.is_duplicate),
        "duplicate_alerts": sum(1 for a in alerts if a.is_duplicate),
        "priority_counts": dict(sorted(priority_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "heartbeat_status": heartbeat.status,
        "active_sources": heartbeat.active_sources,
        "dry_run": True,
        "no_real_notification": True,
    }


def compute_alerts_hash(alerts: list[AlertEvent]) -> str:
    raw = json.dumps([a.to_dict() for a in alerts], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_status_markdown(status: dict) -> str:
    lines = [
        "# Alert Center Status",
        "",
        f"**Total alerts:** {status['total_alerts']}",
        f"**Unique alerts:** {status['unique_alerts']}",
        f"**Duplicate alerts:** {status['duplicate_alerts']}",
        f"**Heartbeat status:** {status['heartbeat_status']}",
        f"**Dry-run:** {status['dry_run']}",
        "",
        "## Priority Breakdown",
        "",
    ]
    for p, count in sorted(status["priority_counts"].items()):
        lines.append(f"- **{p}:** {count}")

    lines.append("")
    lines.append("## Source Breakdown")
    lines.append("")
    for s, count in sorted(status["source_counts"].items()):
        lines.append(f"- **{s}:** {count}")

    lines.append("")
    lines.append("## Active Sources")
    lines.append("")
    for s in status["active_sources"]:
        lines.append(f"- {s}")

    lines.append("")
    lines.append("---")
    lines.append("DRY RUN. NO REAL NOTIFICATIONS SENT.")
    lines.append("")

    return "\n".join(lines)


def write_json(items: list, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps([i.to_dict() for i in items], indent=2),
        encoding="utf-8",
    )


def write_status_json(status: dict, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(status, indent=2), encoding="utf-8")


def write_manifest(data: dict, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
