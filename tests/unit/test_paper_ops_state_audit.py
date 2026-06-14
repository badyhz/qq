"""Unit test: paper ops state auditor."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_ops.paper_state_auditor import audit_store

FIXTURE = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "paper_trading_ops" / "paper_positions.jsonl"


def test_audit_with_fixture() -> None:
    report = audit_store(FIXTURE)
    assert report.records_total == 5
    assert report.audit_status in ("PASS", "WARNING", "FAIL")


def test_audit_verdict_format() -> None:
    report = audit_store(FIXTURE)
    assert "PAPER_STATE_AUDITOR_READY" in report.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in report.final_verdict


def test_audit_nonexistent_store() -> None:
    report = audit_store("/tmp/nonexistent_store_12345.jsonl")
    assert report.records_total == 0
    assert report.audit_status == "PASS"


def test_audit_report_to_dict() -> None:
    report = audit_store(FIXTURE)
    d = report.to_dict()
    assert "audit_id" in d
    assert "audit_status" in d


def test_audit_dry_run_only() -> None:
    report = audit_store(FIXTURE)
    assert report.not_dry_run_count == 0


def main() -> None:
    test_audit_with_fixture()
    test_audit_verdict_format()
    test_audit_nonexistent_store()
    test_audit_report_to_dict()
    test_audit_dry_run_only()
    print("test_paper_ops_state_audit: ALL PASS")


if __name__ == "__main__":
    main()
