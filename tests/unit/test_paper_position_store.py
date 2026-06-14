"""Unit test: paper position store."""
from __future__ import annotations
import pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_pipeline.paper_position_store import (
    load_store, append_new_positions, upsert_position, dedupe_by_plan_id, mark_updated)
from src.paper_trading_pipeline.models import PaperPositionRecord, utc_now_iso


def _tmp_path() -> pathlib.Path:
    return pathlib.Path(tempfile.mktemp(suffix=".jsonl"))


def _make_plan(plan_id="TP_test", symbol="BTCUSDT") -> dict:
    return {"plan_id": plan_id, "signal_id": "SIG_test", "symbol": symbol,
            "timeframe": "5m", "entry_price": 104500.0, "stop_loss": 101400.0,
            "take_profit_1": 109150.0, "take_profit_2": 112150.0, "take_profit_3": 116800.0}


def test_load_empty() -> None:
    p = _tmp_path()
    records = load_store(p)
    assert len(records) == 0


def test_append_and_load() -> None:
    p = _tmp_path()
    plans = [_make_plan()]
    records, added = append_new_positions(plans, p)
    assert added == 1
    assert len(records) == 1


def test_append_dedup_by_plan_id() -> None:
    p = _tmp_path()
    plans = [_make_plan()]
    append_new_positions(plans, p)
    _, added = append_new_positions(plans, p)
    assert added == 0


def test_upsert_new() -> None:
    p = _tmp_path()
    r = PaperPositionRecord(
        record_id="R1", paper_position_id="PP1", plan_id="TP_new",
        symbol="BTCUSDT", timeframe="5m", status="PLANNED",
        entry_price=104500.0, stop_loss=101400.0,
        take_profit_1=109150.0, take_profit_2=112150.0, take_profit_3=116800.0,
        created_at="", updated_at="", source_signal_id="SIG1", dry_run_only=True)
    records = upsert_position(r, p)
    assert len(records) == 1


def test_mark_updated() -> None:
    p = _tmp_path()
    append_new_positions([_make_plan()], p)
    updated = mark_updated("TP_test", "PAPER_OPEN", p)
    assert updated is not None
    assert updated.status == "PAPER_OPEN"


def test_dedupe_by_plan_id() -> None:
    p = _tmp_path()
    append_new_positions([_make_plan()], p)
    append_new_positions([_make_plan()], p)  # should be deduped by append
    removed = dedupe_by_plan_id(p)
    assert removed == 0  # already deduped


def main() -> None:
    test_load_empty()
    test_append_and_load()
    test_append_dedup_by_plan_id()
    test_upsert_new()
    test_mark_updated()
    test_dedupe_by_plan_id()
    print("test_paper_position_store: ALL PASS")


if __name__ == "__main__":
    main()
