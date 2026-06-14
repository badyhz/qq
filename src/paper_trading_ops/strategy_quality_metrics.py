"""Strategy quality metrics — computes win rate, expectancy, etc."""
from __future__ import annotations
import statistics
from collections import Counter, defaultdict
from src.paper_trading_ops.models import StrategyQualityMetrics, new_id, utc_now_iso

CLOSED_STATUSES = ("PAPER_STOPPED", "PAPER_CLOSED_TP3", "PAPER_TIME_STOPPED", "PAPER_CLOSED")
WIN_STATUSES = ("PAPER_TP1_HIT", "PAPER_TP2_HIT", "PAPER_CLOSED_TP3", "PAPER_CLOSED")


def compute_metrics(positions: list[dict]) -> StrategyQualityMetrics:
    total = len(positions)
    closed = [p for p in positions if p.get("status") in CLOSED_STATUSES]
    open_pos = [p for p in positions if p.get("status") in ("PAPER_OPEN", "PAPER_TP1_HIT", "PAPER_TP2_HIT")]
    planned = [p for p in positions if p.get("status") == "PLANNED"]

    tp1 = sum(1 for p in positions if p.get("status") in ("PAPER_TP1_HIT", "PAPER_TP2_HIT", "PAPER_CLOSED_TP3", "PAPER_CLOSED"))
    tp2 = sum(1 for p in positions if p.get("status") in ("PAPER_TP2_HIT", "PAPER_CLOSED_TP3", "PAPER_CLOSED"))
    tp3 = sum(1 for p in positions if p.get("status") in ("PAPER_CLOSED_TP3", "PAPER_CLOSED"))
    stops = sum(1 for p in positions if p.get("status") == "PAPER_STOPPED")
    time_stops = sum(1 for p in positions if p.get("status") == "PAPER_TIME_STOPPED")

    wins = [p for p in closed if p.get("status") in WIN_STATUSES]
    losses = [p for p in closed if p.get("status") not in WIN_STATUSES]

    # Approximate PnL in R for closed positions
    pnl_values: list[float] = []
    for p in closed:
        entry = p.get("entry_price", 0)
        sl = p.get("stop_loss", 0)
        if entry <= 0 or sl <= 0 or entry == sl:
            pnl_values.append(0.0)
            continue
        r = abs(entry - sl)
        if p.get("status") == "PAPER_STOPPED":
            pnl_values.append(-1.0)
        elif p.get("status") == "PAPER_TIME_STOPPED":
            pnl_values.append(-0.5)  # approximate
        elif p.get("status") in ("PAPER_CLOSED_TP3", "PAPER_CLOSED"):
            pnl_values.append(4.0)
        elif p.get("status") == "PAPER_TP2_HIT":
            pnl_values.append(2.5)
        elif p.get("status") == "PAPER_TP1_HIT":
            pnl_values.append(1.5)
        else:
            pnl_values.append(0.0)

    win_rate = len(wins) / len(closed) * 100 if closed else 0.0
    avg_pnl = statistics.mean(pnl_values) if pnl_values else 0.0
    median_pnl = statistics.median(pnl_values) if pnl_values else 0.0
    best_pnl = max(pnl_values) if pnl_values else 0.0
    worst_pnl = min(pnl_values) if pnl_values else 0.0

    win_pnl = [v for v in pnl_values if v > 0]
    loss_pnl = [v for v in pnl_values if v < 0]
    avg_win = statistics.mean(win_pnl) if win_pnl else 0.0
    avg_loss = statistics.mean(loss_pnl) if loss_pnl else 0.0
    win_prob = len(win_pnl) / len(pnl_values) if pnl_values else 0.0
    expectancy = (win_prob * avg_win) + ((1 - win_prob) * avg_loss) if pnl_values else 0.0

    gross_profit = sum(win_pnl) if win_pnl else 0.0
    gross_loss = abs(sum(loss_pnl)) if loss_pnl else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

    bars_values = [p.get("bars_held", 0) for p in closed if p.get("bars_held", 0) > 0]
    avg_bars = statistics.mean(bars_values) if bars_values else 0.0
    max_bars = max(bars_values) if bars_values else 0

    # Symbol breakdown
    sym_data: dict[str, dict] = defaultdict(lambda: {"total": 0, "wins": 0, "losses": 0})
    for p in positions:
        sym = p.get("symbol", "UNKNOWN")
        sym_data[sym]["total"] += 1
        if p.get("status") in CLOSED_STATUSES:
            if p.get("status") in WIN_STATUSES:
                sym_data[sym]["wins"] += 1
            else:
                sym_data[sym]["losses"] += 1
    symbol_breakdown = {s: dict(d) for s, d in sym_data.items()}

    if len(closed) < 20:
        sample = "INSUFFICIENT_SAMPLE"
    elif expectancy > 0:
        sample = "PROMISING"
    else:
        sample = "WEAK"

    return StrategyQualityMetrics(
        metrics_id=new_id("SQM"), created_at=utc_now_iso(),
        total_positions=total, closed_positions=len(closed),
        open_positions=len(open_pos), tp1_count=tp1, tp2_count=tp2,
        tp3_count=tp3, stop_count=stops, time_stop_count=time_stops,
        win_count=len(wins), loss_count=len(losses),
        win_rate=round(win_rate, 2), avg_pnl_r=round(avg_pnl, 4),
        median_pnl_r=round(median_pnl, 4), expectancy_r=round(expectancy, 4),
        best_pnl_r=round(best_pnl, 4), worst_pnl_r=round(worst_pnl, 4),
        profit_factor_placeholder=round(profit_factor, 4),
        avg_bars_held=round(avg_bars, 1), max_bars_held=max_bars,
        symbol_breakdown=symbol_breakdown, sample_status=sample,
        final_verdict=f"STRATEGY_QUALITY_METRICS_READY|CLOSED={len(closed)}|WIN_RATE={win_rate:.1f}%|EXPECTANCY={expectancy:.2f}R|STATUS={sample}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
