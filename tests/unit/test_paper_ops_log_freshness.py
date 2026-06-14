"""Unit test: paper ops log freshness monitor."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_ops.log_freshness_monitor import check_freshness

FIXTURE = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "paper_trading_ops" / "scanner"


def test_freshness_with_fixture() -> None:
    report = check_freshness(str(FIXTURE))
    assert report.signals_file_exists is True
    assert report.scan_detail_file_exists is True
    assert report.freshness_status in ("FRESH", "STALE_WARNING", "STALE_CRITICAL", "NO_DATA")


def test_freshness_verdict_format() -> None:
    report = check_freshness(str(FIXTURE))
    assert "PAPER_OPS_LOG_FRESHNESS_MONITOR_READY" in report.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in report.final_verdict


def test_freshness_nonexistent_path() -> None:
    report = check_freshness("/tmp/nonexistent_scanner_path_12345")
    assert report.freshness_status == "NO_DATA"
    assert report.signals_file_exists is False


def test_freshness_report_to_dict() -> None:
    report = check_freshness(str(FIXTURE))
    d = report.to_dict()
    assert "report_id" in d
    assert "freshness_status" in d


def main() -> None:
    test_freshness_with_fixture()
    test_freshness_verdict_format()
    test_freshness_nonexistent_path()
    test_freshness_report_to_dict()
    print("test_paper_ops_log_freshness: ALL PASS")


if __name__ == "__main__":
    main()
