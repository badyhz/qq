"""Unit test: paper ops runtime layout."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_deployment.runtime_layout import check_layout

ROOT = str(pathlib.Path(__file__).resolve().parent.parent.parent)


def test_layout_with_real_repo() -> None:
    report = check_layout(ROOT)
    assert report.layout_status in ("READY", "CREATABLE", "INCOMPLETE")


def test_layout_required_dirs() -> None:
    report = check_layout(ROOT)
    assert len(report.required_dirs) >= 5


def test_layout_verdict_format() -> None:
    report = check_layout(ROOT)
    assert "PAPER_OPS_RUNTIME_LAYOUT_READY" in report.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in report.final_verdict


def test_layout_to_dict() -> None:
    report = check_layout(ROOT)
    d = report.to_dict()
    assert "layout_id" in d
    assert "required_dirs" in d


def main() -> None:
    test_layout_with_real_repo()
    test_layout_required_dirs()
    test_layout_verdict_format()
    test_layout_to_dict()
    print("test_paper_ops_runtime_layout: ALL PASS")


if __name__ == "__main__":
    main()
