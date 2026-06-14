"""Daily paper trading review."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from src.paper_trading_pipeline.models import (
    ScannerLogSnapshot, DedupedSignalBatch, TradePlanBatch,
    PaperPositionRecord, ReplaySchedule, DailyPaperReview,
    new_id, utc_now_iso,
)


def generate_daily_review(
    snapshot: ScannerLogSnapshot,
    deduped: DedupedSignalBatch,
    plan_batch: TradePlanBatch,
    positions: list[PaperPositionRecord],
    schedule: ReplaySchedule | None = None,
) -> DailyPaperReview:
    symbol_counter = Counter(p.symbol for p in positions)
    top_symbols = [s for s, _ in symbol_counter.most_common(5)]

    open_count = sum(1 for p in positions if p.status == "PAPER_OPEN")
    closed_count = sum(1 for p in positions if p.status in (
        "PAPER_STOPPED", "PAPER_CLOSED_TP3", "PAPER_TIME_STOPPED"))
    tp1 = sum(1 for p in positions if p.status in ("PAPER_TP1_HIT", "PAPER_TP2_HIT", "PAPER_CLOSED_TP3"))
    tp2 = sum(1 for p in positions if p.status in ("PAPER_TP2_HIT", "PAPER_CLOSED_TP3"))
    tp3 = sum(1 for p in positions if p.status == "PAPER_CLOSED_TP3")
    stops = sum(1 for p in positions if p.status == "PAPER_STOPPED")
    time_stops = sum(1 for p in positions if p.status == "PAPER_TIME_STOPPED")

    total_closed = closed_count
    win_rate = (tp1 / total_closed * 100) if total_closed > 0 else 0.0

    risk_notes: list[str] = []
    if plan_batch.plans_rejected > 0:
        risk_notes.append(f"{plan_batch.plans_rejected} plans rejected for high risk")
    if stops > tp1 and stops > 0:
        risk_notes.append("More stops than wins — review entry criteria")
    if snapshot.errors_count > 0:
        risk_notes.append(f"Scanner has {snapshot.errors_count} error lines")

    data_notes: list[str] = []
    if snapshot.source_status != "ALL_SOURCES_PRESENT":
        data_notes.append("Not all scanner source files present")
    if deduped.duplicate_count > 0:
        data_notes.append(f"{deduped.duplicate_count} duplicate signals removed")

    actions: list[str] = []
    if plan_batch.plans_created == 0:
        actions.append("No trade plans — verify scanner signals")
    if stops > 0 and stops > tp1:
        actions.append("Consider tightening entry criteria")
    if not actions:
        actions.append("Continue monitoring")

    return DailyPaperReview(
        review_id=new_id("DPR"),
        created_at=utc_now_iso(),
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        raw_signals=deduped.raw_count,
        deduped_signals=deduped.deduped_count,
        trade_plans_created=plan_batch.plans_created,
        paper_positions_total=len(positions),
        paper_open_count=open_count,
        paper_closed_count=closed_count,
        tp1_count=tp1, tp2_count=tp2, tp3_count=tp3,
        stop_count=stops, time_stop_count=time_stops,
        win_rate_placeholder=round(win_rate, 2),
        expectancy_r_placeholder=0.0,
        top_symbols=top_symbols,
        risk_notes=risk_notes,
        data_quality_notes=data_notes,
        next_actions=actions,
        final_verdict=f"DAILY_PAPER_TRADING_REVIEW_READY|PLANS={plan_batch.plans_created}|POSITIONS={len(positions)}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
