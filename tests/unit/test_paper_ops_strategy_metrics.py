"""Unit test: paper ops strategy quality metrics."""
from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_ops.strategy_quality_metrics import compute_metrics

FIXTURE = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "paper_trading_ops" / "paper_positions.jsonl"


def _load_positions() -> list[dict]:
    positions = []
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            positions.append(json.loads(line))
    return positions


def test_metrics_with_fixture() -> None:
    positions = _load_positions()
    m = compute_metrics(positions)
    assert m.total_positions == 5
    assert m.closed_positions == 4  # TP3, STOP, CLOSED, TIME_STOPPED
    assert m.open_positions == 1    # TP1_HIT


def test_metrics_win_rate() -> None:
    positions = _load_positions()
    m = compute_metrics(positions)
    # wins: TP3, CLOSED = 2; losses: STOP, TIME_STOPPED = 2
    assert m.win_rate == 50.0


def test_metrics_sample_status() -> None:
    positions = _load_positions()
    m = compute_metrics(positions)
    assert m.sample_status == "INSUFFICIENT_SAMPLE"  # only 4 closed, need 20+


def test_metrics_verdict_format() -> None:
    positions = _load_positions()
    m = compute_metrics(positions)
    assert "STRATEGY_QUALITY_METRICS_READY" in m.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in m.final_verdict


def test_metrics_empty() -> None:
    m = compute_metrics([])
    assert m.total_positions == 0
    assert m.win_rate == 0.0


def test_metrics_to_dict() -> None:
    positions = _load_positions()
    m = compute_metrics(positions)
    d = m.to_dict()
    assert "metrics_id" in d
    assert "symbol_breakdown" in d


def main() -> None:
    test_metrics_with_fixture()
    test_metrics_win_rate()
    test_metrics_sample_status()
    test_metrics_verdict_format()
    test_metrics_empty()
    test_metrics_to_dict()
    print("test_paper_ops_strategy_metrics: ALL PASS")


if __name__ == "__main__":
    main()
