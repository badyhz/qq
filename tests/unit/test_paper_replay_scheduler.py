"""Unit test: paper replay scheduler."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_pipeline.paper_replay_scheduler import build_replay_schedule
from src.paper_trading_pipeline.models import PaperPositionRecord


def _make_record(status="PLANNED") -> PaperPositionRecord:
    return PaperPositionRecord(
        record_id="R1", paper_position_id="PP1", plan_id="TP1",
        symbol="BTCUSDT", timeframe="5m", status=status,
        entry_price=104500.0, stop_loss=101400.0,
        take_profit_1=109150.0, take_profit_2=112150.0, take_profit_3=116800.0,
        created_at="", updated_at="", source_signal_id="SIG1", dry_run_only=True)


def test_schedule_planned() -> None:
    records = [_make_record("PLANNED")]
    s = build_replay_schedule(records)
    assert s.needs_entry_check == 1
    assert s.needs_exit_check == 0


def test_schedule_open() -> None:
    records = [_make_record("PAPER_OPEN")]
    s = build_replay_schedule(records)
    assert s.needs_exit_check == 1


def test_schedule_closed() -> None:
    records = [_make_record("PAPER_STOPPED")]
    s = build_replay_schedule(records)
    assert s.already_closed == 1


def test_schedule_mixed() -> None:
    records = [_make_record("PLANNED"), _make_record("PAPER_OPEN"), _make_record("PAPER_STOPPED")]
    s = build_replay_schedule(records)
    assert s.total_positions == 3
    assert s.needs_entry_check == 1
    assert s.needs_exit_check == 1
    assert s.already_closed == 1


def test_schedule_verdict() -> None:
    s = build_replay_schedule([])
    assert "REPLAY_SCHEDULER_READY" in s.final_verdict


def test_schedule_actions() -> None:
    records = [_make_record("PLANNED")]
    s = build_replay_schedule(records)
    assert any("PLANNED" in a for a in s.next_actions)


def main() -> None:
    test_schedule_planned()
    test_schedule_open()
    test_schedule_closed()
    test_schedule_mixed()
    test_schedule_verdict()
    test_schedule_actions()
    print("test_paper_replay_scheduler: ALL PASS")


if __name__ == "__main__":
    main()
