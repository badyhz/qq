"""Unit test: scanner log source."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_pipeline.scanner_log_source import load_scanner_snapshot

FIXTURE = str(pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "paper_trading_pipeline" / "scanner")


def test_snapshot_signals() -> None:
    snap = load_scanner_snapshot(FIXTURE)
    assert snap.signals_count == 5, f"Expected 5, got {snap.signals_count}"


def test_snapshot_alerts() -> None:
    snap = load_scanner_snapshot(FIXTURE)
    assert snap.alerts_count == 3


def test_snapshot_errors() -> None:
    snap = load_scanner_snapshot(FIXTURE)
    assert snap.errors_count == 1


def test_snapshot_source_status() -> None:
    snap = load_scanner_snapshot(FIXTURE)
    assert snap.source_status == "ALL_SOURCES_PRESENT"


def test_snapshot_verdict() -> None:
    snap = load_scanner_snapshot(FIXTURE)
    assert "SCANNER_LOG_SOURCE_READY" in snap.final_verdict


def test_snapshot_nonexistent() -> None:
    snap = load_scanner_snapshot("/nonexistent")
    assert snap.signals_count == 0


def main() -> None:
    test_snapshot_signals()
    test_snapshot_alerts()
    test_snapshot_errors()
    test_snapshot_source_status()
    test_snapshot_verdict()
    test_snapshot_nonexistent()
    print("test_paper_trading_scanner_log_source: ALL PASS")


if __name__ == "__main__":
    main()
