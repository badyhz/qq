"""Signal quality dashboard — grades signal-to-outcome pipeline."""
from __future__ import annotations
from collections import Counter, defaultdict
from src.paper_trading_ops.models import SignalQualityDashboard, new_id, utc_now_iso

WIN_STATUSES = ("PAPER_TP1_HIT", "PAPER_TP2_HIT", "PAPER_CLOSED_TP3", "PAPER_CLOSED")
CLOSED_STATUSES = ("PAPER_STOPPED", "PAPER_CLOSED_TP3", "PAPER_TIME_STOPPED", "PAPER_CLOSED")


def build_dashboard(
    raw_signals: int,
    deduped_signals: int,
    plans_created: int,
    plans_rejected: int,
    positions: list[dict],
    expectancy_r: float = 0.0,
    win_rate: float = 0.0,
    period: str = "all_time",
) -> SignalQualityDashboard:
    total = len(positions)
    open_pos = sum(1 for p in positions if p.get("status") in ("PAPER_OPEN", "PAPER_TP1_HIT", "PAPER_TP2_HIT"))
    closed = sum(1 for p in positions if p.get("status") in CLOSED_STATUSES)
    tp_hit = sum(1 for p in positions if p.get("status") in WIN_STATUSES)
    stop = sum(1 for p in positions if p.get("status") == "PAPER_STOPPED")

    sym_signals: Counter = Counter()
    sym_tp: Counter = Counter()
    sym_stop: Counter = Counter()
    for p in positions:
        sym = p.get("symbol", "UNKNOWN")
        sym_signals[sym] += 1
        if p.get("status") in WIN_STATUSES:
            sym_tp[sym] += 1
        if p.get("status") == "PAPER_STOPPED":
            sym_stop[sym] += 1

    top_signal = [s for s, _ in sym_signals.most_common(5)]
    top_tp = [s for s, _ in sym_tp.most_common(5)]
    top_stop = [s for s, _ in sym_stop.most_common(5)]

    # Best/worst by net TP - STOP
    sym_net: dict[str, int] = defaultdict(int)
    for s in set(list(sym_tp.keys()) + list(sym_stop.keys())):
        sym_net[s] = sym_tp[s] - sym_stop[s]
    best = sorted(sym_net, key=lambda s: sym_net[s], reverse=True)[:3]
    worst = sorted(sym_net, key=lambda s: sym_net[s])[:3]

    notes: list[str] = []
    if closed < 20:
        grade = "INSUFFICIENT_DATA"
        notes.append(f"Only {closed} closed trades — need 20+ for grading")
    elif expectancy_r > 0.5 and win_rate >= 50:
        grade = "A"
        notes.append(f"Strong edge: expectancy={expectancy_r:.2f}R, win_rate={win_rate:.1f}%")
    elif expectancy_r > 0 and win_rate >= 40:
        grade = "B"
        notes.append(f"Moderate edge: expectancy={expectancy_r:.2f}R, win_rate={win_rate:.1f}%")
    elif expectancy_r > -0.1:
        grade = "C"
        notes.append(f"Marginal: expectancy={expectancy_r:.2f}R — needs improvement")
    else:
        grade = "D"
        notes.append(f"Negative edge: expectancy={expectancy_r:.2f}R — strategy losing money")

    if plans_rejected > plans_created:
        notes.append(f"More plans rejected ({plans_rejected}) than created ({plans_created})")

    return SignalQualityDashboard(
        dashboard_id=new_id("SQD"), created_at=utc_now_iso(), period=period,
        raw_signals=raw_signals, deduped_signals=deduped_signals,
        plans_created=plans_created, plans_rejected=plans_rejected,
        paper_positions_total=total, open_positions=open_pos,
        closed_positions=closed, tp_hit_count=tp_hit, stop_count=stop,
        top_symbols_by_signal=top_signal, top_symbols_by_tp=top_tp,
        top_symbols_by_stop=top_stop, best_symbols=best, worst_symbols=worst,
        quality_grade=grade, quality_notes=notes,
        final_verdict=f"SIGNAL_QUALITY_DASHBOARD_READY|GRADE={grade}|CLOSED={closed}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
