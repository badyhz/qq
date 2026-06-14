"""Scanner log source — reads scanner outputs into pipeline."""
from __future__ import annotations
import csv, json, pathlib
from src.paper_trading_pipeline.models import ScannerLogSnapshot, new_id, utc_now_iso


def _count_lines(path: pathlib.Path) -> int:
    if not path.exists():
        return 0
    try:
        content = path.read_text(encoding="utf-8").strip()
        return len(content.splitlines()) if content else 0
    except Exception:
        return 0


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


def load_scanner_snapshot(scanner_path: str) -> ScannerLogSnapshot:
    root = pathlib.Path(scanner_path)
    signals_path = root / "data" / "signals.csv"
    alerts_path = root / "logs" / "alerts.jsonl"
    scan_detail_path = root / "logs" / "scan_detail.jsonl"
    errors_path = root / "logs" / "errors.log"

    signals = _read_csv(signals_path)
    alerts = _read_jsonl(alerts_path)
    scan_details = _read_jsonl(scan_detail_path)
    errors = _count_lines(errors_path)

    source_files = {
        "data/signals.csv": signals_path.exists(),
        "logs/alerts.jsonl": alerts_path.exists(),
        "logs/scan_detail.jsonl": scan_detail_path.exists(),
        "logs/errors.log": errors_path.exists(),
    }

    latest_signal = signals[-1].get("time", "") if signals else None
    latest_alert = alerts[-1].get("signal_time", "") if alerts else None

    all_present = all(source_files.values())
    status = "ALL_SOURCES_PRESENT" if all_present else "PARTIAL_SOURCES"

    return ScannerLogSnapshot(
        snapshot_id=new_id("SNAP"),
        scanner_path=str(root),
        signals_count=len(signals),
        alerts_count=len(alerts),
        scan_detail_count=len(scan_details),
        errors_count=errors,
        latest_signal_time=latest_signal,
        latest_alert_time=latest_alert,
        source_files=source_files,
        source_status=status,
        final_verdict=f"PAPER_TRADING_SCANNER_LOG_SOURCE_READY|SIGNALS={len(signals)}|ALERTS={len(alerts)}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
