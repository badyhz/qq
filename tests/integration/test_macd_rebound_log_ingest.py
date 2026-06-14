"""Integration test: MACD rebound log ingest."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.external_scanner_integrations.macd_rebound_log_ingest import ingest_logs, render_report

FIXTURE = str(pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "macd_rebound_scanner")


def test_ingest_signals() -> None:
    result = ingest_logs(FIXTURE)
    assert result.total_signals == 3, f"Expected 3 signals, got {result.total_signals}"


def test_ingest_alerts() -> None:
    result = ingest_logs(FIXTURE)
    assert result.total_alerts == 4, f"Expected 4 alerts, got {result.total_alerts}"


def test_ingest_dry_run_alerts() -> None:
    result = ingest_logs(FIXTURE)
    assert result.dry_run_alerts == 3, f"Expected 3 dry_run, got {result.dry_run_alerts}"


def test_ingest_failed_alerts() -> None:
    result = ingest_logs(FIXTURE)
    assert result.failed_alerts == 1, f"Expected 1 failed, got {result.failed_alerts}"


def test_ingest_error_count() -> None:
    result = ingest_logs(FIXTURE)
    assert result.error_count == 1, f"Expected 1 error, got {result.error_count}"


def test_ingest_top_symbols() -> None:
    result = ingest_logs(FIXTURE)
    assert len(result.top_symbols) > 0


def test_ingest_verdict() -> None:
    result = ingest_logs(FIXTURE)
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in result.final_verdict


def test_render_report() -> None:
    result = ingest_logs(FIXTURE)
    md = render_report(result)
    assert "# MACD Rebound Log Ingest" in md


def main() -> None:
    test_ingest_signals()
    test_ingest_alerts()
    test_ingest_dry_run_alerts()
    test_ingest_failed_alerts()
    test_ingest_error_count()
    test_ingest_top_symbols()
    test_ingest_verdict()
    test_render_report()
    print("test_macd_rebound_log_ingest: ALL PASS")


if __name__ == "__main__":
    main()
