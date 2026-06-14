"""Unit test: paper ops deployment preflight."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_deployment.preflight_check import run_preflight

ROOT = str(pathlib.Path(__file__).resolve().parent.parent.parent)
FIXTURE_SCANNER = str(pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "paper_trading_deployment" / "scanner")


def test_preflight_with_real_repo() -> None:
    report = run_preflight(ROOT, FIXTURE_SCANNER)
    assert report.preflight_status in ("PASS", "FAIL")
    assert report.checks_passed > 0


def test_preflight_verdict_format() -> None:
    report = run_preflight(ROOT, FIXTURE_SCANNER)
    assert "PAPER_OPS_DEPLOYMENT_PREFLIGHT_READY" in report.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in report.final_verdict


def test_preflight_missing_scanner() -> None:
    report = run_preflight(ROOT, "/tmp/nonexistent_scanner_12345")
    assert any("Scanner path" in w for w in report.warnings)


def test_preflight_missing_repo() -> None:
    report = run_preflight("/tmp/nonexistent_repo_12345", FIXTURE_SCANNER)
    assert report.preflight_status == "FAIL"
    assert len(report.failures) > 0


def test_preflight_to_dict() -> None:
    report = run_preflight(ROOT, FIXTURE_SCANNER)
    d = report.to_dict()
    assert "report_id" in d
    assert "checks_total" in d


def main() -> None:
    test_preflight_with_real_repo()
    test_preflight_verdict_format()
    test_preflight_missing_scanner()
    test_preflight_missing_repo()
    test_preflight_to_dict()
    print("test_paper_ops_deployment_preflight: ALL PASS")


if __name__ == "__main__":
    main()
