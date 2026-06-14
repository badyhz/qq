"""Paper replay scheduler — determines which positions need updating."""
from __future__ import annotations
from src.paper_trading_pipeline.models import PaperPositionRecord, ReplaySchedule, new_id, utc_now_iso

CLOSED_STATUSES = ("PAPER_STOPPED", "PAPER_CLOSED_TP3", "PAPER_TIME_STOPPED")


def build_replay_schedule(records: list[PaperPositionRecord]) -> ReplaySchedule:
    needs_entry = 0
    needs_exit = 0
    closed = 0
    stale = 0
    actions: list[str] = []

    for r in records:
        if r.status == "PLANNED":
            needs_entry += 1
        elif r.status == "PAPER_OPEN":
            needs_exit += 1
        elif r.status in ("PAPER_TP1_HIT", "PAPER_TP2_HIT"):
            needs_exit += 1
        elif r.status in CLOSED_STATUSES:
            closed += 1
        else:
            stale += 1

    if needs_entry > 0:
        actions.append(f"Check {needs_entry} PLANNED positions for entry")
    if needs_exit > 0:
        actions.append(f"Check {needs_exit} open positions for TP/STOP")
    if stale > 0:
        actions.append(f"Review {stale} positions with unknown status")
    if not actions:
        actions.append("No positions need updating")

    return ReplaySchedule(
        schedule_id=new_id("RS"),
        created_at=utc_now_iso(),
        total_positions=len(records),
        needs_entry_check=needs_entry,
        needs_exit_check=needs_exit,
        already_closed=closed,
        stale_positions=stale,
        next_actions=actions,
        final_verdict=f"PAPER_REPLAY_SCHEDULER_READY|TOTAL={len(records)}|NEEDS_ENTRY={needs_entry}|NEEDS_EXIT={needs_exit}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
