"""Paper position updater — simulates TP/STOP/TIME_STOP from OHLCV data."""
from __future__ import annotations
import csv, pathlib
from src.paper_trading_pipeline.models import PaperPositionRecord, new_id, utc_now_iso

MAX_HOLD_BARS = 48


def _read_ohlcv(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def update_position_from_ohlcv(
    record: PaperPositionRecord,
    ohlcv: list[dict],
    max_hold_bars: int = MAX_HOLD_BARS,
) -> PaperPositionRecord:
    if record.status in ("PAPER_STOPPED", "PAPER_CLOSED_TP3", "PAPER_TIME_STOPPED"):
        return record

    entry_low = record.entry_price * 0.995
    entry_high = record.entry_price * 1.005
    entered = record.status != "PLANNED"
    entry_bar = 0
    now = utc_now_iso()

    for i, bar in enumerate(ohlcv):
        high = float(bar.get("high", 0))
        low = float(bar.get("low", 0))

        if not entered:
            if high >= entry_low and low <= entry_high:
                entered = True
                entry_bar = i
                record = PaperPositionRecord(
                    record_id=record.record_id,
                    paper_position_id=record.paper_position_id,
                    plan_id=record.plan_id, symbol=record.symbol,
                    timeframe=record.timeframe, status="PAPER_OPEN",
                    entry_price=record.entry_price, stop_loss=record.stop_loss,
                    take_profit_1=record.take_profit_1,
                    take_profit_2=record.take_profit_2,
                    take_profit_3=record.take_profit_3,
                    created_at=record.created_at, updated_at=now,
                    source_signal_id=record.source_signal_id,
                    dry_run_only=True,
                )
        else:
            bars_held = i - entry_bar

            # Conservative: stop loss first
            if low <= record.stop_loss:
                return PaperPositionRecord(
                    record_id=record.record_id,
                    paper_position_id=record.paper_position_id,
                    plan_id=record.plan_id, symbol=record.symbol,
                    timeframe=record.timeframe, status="PAPER_STOPPED",
                    entry_price=record.entry_price, stop_loss=record.stop_loss,
                    take_profit_1=record.take_profit_1,
                    take_profit_2=record.take_profit_2,
                    take_profit_3=record.take_profit_3,
                    created_at=record.created_at, updated_at=now,
                    source_signal_id=record.source_signal_id,
                    dry_run_only=True,
                )

            if high >= record.take_profit_3:
                return PaperPositionRecord(
                    record_id=record.record_id,
                    paper_position_id=record.paper_position_id,
                    plan_id=record.plan_id, symbol=record.symbol,
                    timeframe=record.timeframe, status="PAPER_CLOSED_TP3",
                    entry_price=record.entry_price, stop_loss=record.stop_loss,
                    take_profit_1=record.take_profit_1,
                    take_profit_2=record.take_profit_2,
                    take_profit_3=record.take_profit_3,
                    created_at=record.created_at, updated_at=now,
                    source_signal_id=record.source_signal_id,
                    dry_run_only=True,
                )

            if high >= record.take_profit_2:
                record = PaperPositionRecord(
                    record_id=record.record_id,
                    paper_position_id=record.paper_position_id,
                    plan_id=record.plan_id, symbol=record.symbol,
                    timeframe=record.timeframe, status="PAPER_TP2_HIT",
                    entry_price=record.entry_price, stop_loss=record.stop_loss,
                    take_profit_1=record.take_profit_1,
                    take_profit_2=record.take_profit_2,
                    take_profit_3=record.take_profit_3,
                    created_at=record.created_at, updated_at=now,
                    source_signal_id=record.source_signal_id,
                    dry_run_only=True,
                )

            if high >= record.take_profit_1 and record.status not in ("PAPER_TP2_HIT",):
                record = PaperPositionRecord(
                    record_id=record.record_id,
                    paper_position_id=record.paper_position_id,
                    plan_id=record.plan_id, symbol=record.symbol,
                    timeframe=record.timeframe, status="PAPER_TP1_HIT",
                    entry_price=record.entry_price, stop_loss=record.stop_loss,
                    take_profit_1=record.take_profit_1,
                    take_profit_2=record.take_profit_2,
                    take_profit_3=record.take_profit_3,
                    created_at=record.created_at, updated_at=now,
                    source_signal_id=record.source_signal_id,
                    dry_run_only=True,
                )

            if bars_held >= max_hold_bars and record.status not in ("PAPER_TP2_HIT", "PAPER_CLOSED_TP3"):
                return PaperPositionRecord(
                    record_id=record.record_id,
                    paper_position_id=record.paper_position_id,
                    plan_id=record.plan_id, symbol=record.symbol,
                    timeframe=record.timeframe, status="PAPER_TIME_STOPPED",
                    entry_price=record.entry_price, stop_loss=record.stop_loss,
                    take_profit_1=record.take_profit_1,
                    take_profit_2=record.take_profit_2,
                    take_profit_3=record.take_profit_3,
                    created_at=record.created_at, updated_at=now,
                    source_signal_id=record.source_signal_id,
                    dry_run_only=True,
                )

    return record


def update_positions_batch(
    records: list[PaperPositionRecord],
    ohlcv_map: dict[str, list[dict]],
    max_hold_bars: int = MAX_HOLD_BARS,
) -> tuple[list[PaperPositionRecord], int]:
    updated_count = 0
    results: list[PaperPositionRecord] = []
    for r in records:
        ohlcv = ohlcv_map.get(r.symbol, [])
        if ohlcv:
            new_r = update_position_from_ohlcv(r, ohlcv, max_hold_bars)
            if new_r.status != r.status:
                updated_count += 1
            results.append(new_r)
        else:
            results.append(r)
    return results, updated_count
