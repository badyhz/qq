"""MACD rebound scanner log ingestion."""
from __future__ import annotations
import csv, json, pathlib, uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class LogIngestResult:
    ingest_id: str
    created_at: str
    scanner_path: str
    total_signals: int
    total_alerts: int
    sent_alerts: int
    dry_run_alerts: int
    failed_alerts: int
    latest_signal_time: str | None
    latest_alert_time: str | None
    top_symbols: list[str]
    error_count: int
    final_verdict: str
    def to_dict(self) -> dict:
        return {"ingest_id": self.ingest_id, "created_at": self.created_at,
                "scanner_path": self.scanner_path, "total_signals": self.total_signals,
                "total_alerts": self.total_alerts, "sent_alerts": self.sent_alerts,
                "dry_run_alerts": self.dry_run_alerts, "failed_alerts": self.failed_alerts,
                "latest_signal_time": self.latest_signal_time,
                "latest_alert_time": self.latest_alert_time,
                "top_symbols": self.top_symbols, "error_count": self.error_count,
                "final_verdict": self.final_verdict}


def _read_csv(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _read_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return rows


def _count_errors(path: pathlib.Path) -> int:
    if not path.exists():
        return 0
    try:
        content = path.read_text(encoding="utf-8").strip()
        return len(content.splitlines()) if content else 0
    except Exception:
        return 0


def ingest_logs(scanner_path: str) -> LogIngestResult:
    root = pathlib.Path(scanner_path)
    signals = _read_csv(root / "data" / "signals.csv")
    alerts = _read_jsonl(root / "logs" / "alerts.jsonl")
    _scan_detail = _read_jsonl(root / "logs" / "scan_detail.jsonl")  # noqa: F841
    error_count = _count_errors(root / "logs" / "errors.log")
    sent = sum(1 for a in alerts if a.get("sent"))
    dry_run = sum(1 for a in alerts if a.get("dry_run"))
    failed = sum(1 for a in alerts if a.get("error_message"))
    symbols = Counter()
    for s in signals:
        sym = s.get("symbol", "")
        if sym:
            symbols[sym] += 1
    top = [s for s, _ in symbols.most_common(10)]
    latest_signal = signals[-1].get("time") if signals else None
    latest_alert = alerts[-1].get("signal_time") if alerts else None
    return LogIngestResult(
        ingest_id=f"MRL_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        scanner_path=str(root),
        total_signals=len(signals),
        total_alerts=len(alerts),
        sent_alerts=sent,
        dry_run_alerts=dry_run,
        failed_alerts=failed,
        latest_signal_time=latest_signal,
        latest_alert_time=latest_alert,
        top_symbols=top,
        error_count=error_count,
        final_verdict=f"MACD_REBOUND_LOG_INGEST_READY|SIGNALS={len(signals)}|ALERTS={len(alerts)}|ERRORS={error_count}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def write_result(result: LogIngestResult, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


def render_report(result: LogIngestResult) -> str:
    lines = ["# MACD Rebound Log Ingest", "",
        f"**ingest_id={result.ingest_id}**",
        f"**scanner_path={result.scanner_path}**", "",
        "## Summary", "",
        f"- total_signals: {result.total_signals}",
        f"- total_alerts: {result.total_alerts}",
        f"- sent_alerts: {result.sent_alerts}",
        f"- dry_run_alerts: {result.dry_run_alerts}",
        f"- failed_alerts: {result.failed_alerts}",
        f"- latest_signal_time: {result.latest_signal_time}",
        f"- latest_alert_time: {result.latest_alert_time}",
        f"- error_count: {result.error_count}", "",
        "## Top Symbols", ""]
    for s in result.top_symbols:
        lines.append(f"- {s}")
    lines.extend(["", "## Conclusion", "", result.final_verdict, ""])
    return "\n".join(lines)
