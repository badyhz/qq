"""Unit test: paper ops signal quality dashboard."""
from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_ops.signal_quality_dashboard import build_dashboard

FIXTURE = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "paper_trading_ops" / "paper_positions.jsonl"


def _load_positions() -> list[dict]:
    positions = []
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            positions.append(json.loads(line))
    return positions


def test_dashboard_with_fixture() -> None:
    positions = _load_positions()
    d = build_dashboard(10, 8, 6, 2, positions, expectancy_r=0.5, win_rate=50.0)
    assert d.paper_positions_total == 5
    assert d.closed_positions == 4


def test_dashboard_grade_insufficient() -> None:
    positions = _load_positions()
    d = build_dashboard(10, 8, 6, 2, positions, expectancy_r=0.0, win_rate=0.0)
    assert d.quality_grade == "INSUFFICIENT_DATA"  # only 4 closed


def test_dashboard_grade_a() -> None:
    # Need 20+ closed positions for grading
    positions = _load_positions()
    # Create 20+ closed positions by repeating
    many = []
    for _ in range(6):
        many.extend(positions)
    d = build_dashboard(60, 48, 36, 12, many, expectancy_r=0.6, win_rate=55.0)
    assert d.quality_grade == "A"


def test_dashboard_grade_d() -> None:
    many = []
    for _ in range(6):
        many.extend(positions := _load_positions())
    d = build_dashboard(60, 48, 36, 12, many, expectancy_r=-0.5, win_rate=20.0)
    assert d.quality_grade == "D"


def test_dashboard_verdict_format() -> None:
    positions = _load_positions()
    d = build_dashboard(10, 8, 6, 2, positions)
    assert "SIGNAL_QUALITY_DASHBOARD_READY" in d.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in d.final_verdict


def test_dashboard_to_dict() -> None:
    positions = _load_positions()
    d = build_dashboard(10, 8, 6, 2, positions)
    assert "dashboard_id" in d.to_dict()


def main() -> None:
    test_dashboard_with_fixture()
    test_dashboard_grade_insufficient()
    test_dashboard_grade_a()
    test_dashboard_grade_d()
    test_dashboard_verdict_format()
    test_dashboard_to_dict()
    print("test_paper_ops_signal_dashboard: ALL PASS")


if __name__ == "__main__":
    main()
