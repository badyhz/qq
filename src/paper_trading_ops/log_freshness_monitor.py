"""Log freshness monitor — checks if scanner is still producing logs."""
from __future__ import annotations
import csv, json, pathlib
from datetime import datetime, timezone, timedelta
from src.paper_trading_ops.models import LogFreshnessReport, new_id, utc_now_iso


def _parse_time(t: str) -> datetime | None:
    if not t:
        return None
    t = t.strip().replace("T", " ").split("+")[0].split("Z")[0]
    if "." in t:
        t = t.split(".")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            continue
    return None


def _latest_csv_time(path: pathlib.Path) -> str | None:
    if not path.exists():
        return None
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if rows:
            return rows[-1].get("time", "")
    except Exception:
        pass
    return None


def _latest_jsonl_time(path: pathlib.Path, field: str = "signal_time") -> str | None:
    if not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        for line in reversed(lines):
            line = line.strip()
            if line:
                d = json.loads(line)
                return d.get(field, d.get("signal_time", d.get("round_id", "")))
    except Exception:
        pass
    return None


def _minutes_since(t: str | None) -> float | None:
    if not t:
        return None
    dt = _parse_time(t)
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    return delta.total_seconds() / 60


def check_freshness(scanner_path: str) -> LogFreshnessReport:
    root = pathlib.Path(scanner_path)
    signals_path = root / "data" / "signals.csv"
    alerts_path = root / "logs" / "alerts.jsonl"
    scan_detail_path = root / "logs" / "scan_detail.jsonl"
    errors_path = root / "logs" / "errors.log"

    latest_signal = _latest_csv_time(signals_path)
    latest_alert = _latest_jsonl_time(alerts_path)
    latest_scan = _latest_jsonl_time(scan_detail_path)

    mins_signal = _minutes_since(latest_signal)
    mins_alert = _minutes_since(latest_alert)
    mins_scan = _minutes_since(latest_scan)

    reasons: list[str] = []
    if not scan_detail_path.exists():
        status = "NO_DATA"
        reasons.append("scan_detail.jsonl not found")
    elif mins_scan is None:
        status = "NO_DATA"
        reasons.append("Cannot parse latest scan_detail time")
    elif mins_scan <= 30:
        status = "FRESH"
    elif mins_scan <= 120:
        status = "STALE_WARNING"
        reasons.append(f"Latest scan_detail is {mins_scan:.0f}min old (>30min)")
    else:
        status = "STALE_CRITICAL"
        reasons.append(f"Latest scan_detail is {mins_scan:.0f}min old (>120min)")

    if mins_signal is not None and mins_signal > 120:
        reasons.append(f"Latest signal is {mins_signal:.0f}min old")
    if mins_alert is not None and mins_alert > 120:
        reasons.append(f"Latest alert is {mins_alert:.0f}min old")

    return LogFreshnessReport(
        report_id=new_id("LFR"),
        created_at=utc_now_iso(),
        scanner_path=str(root),
        signals_file_exists=signals_path.exists(),
        alerts_file_exists=alerts_path.exists(),
        scan_detail_file_exists=scan_detail_path.exists(),
        errors_file_exists=errors_path.exists(),
        latest_signal_time=latest_signal,
        latest_alert_time=latest_alert,
        latest_scan_detail_time=latest_scan,
        minutes_since_latest_signal=round(mins_signal, 1) if mins_signal is not None else None,
        minutes_since_latest_alert=round(mins_alert, 1) if mins_alert is not None else None,
        minutes_since_latest_scan_detail=round(mins_scan, 1) if mins_scan is not None else None,
        freshness_status=status,
        stale_reasons=reasons,
        final_verdict=f"PAPER_OPS_LOG_FRESHNESS_MONITOR_READY|STATUS={status}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
