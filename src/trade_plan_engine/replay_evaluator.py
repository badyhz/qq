"""Replay evaluator: statistics from paper positions."""
from __future__ import annotations
import json, pathlib, statistics
from dataclasses import dataclass
from datetime import datetime, timezone

from src.trade_plan_engine.models import PaperPosition, new_id, utc_now_iso


@dataclass(frozen=True)
class ReplayStats:
    evaluator_id: str
    created_at: str
    total_plans: int
    paper_open_count: int
    tp1_count: int
    tp2_count: int
    tp3_count: int
    stop_count: int
    time_stop_count: int
    invalidated_count: int
    win_rate: float
    avg_pnl_r: float
    median_pnl_r: float
    max_loss_r: float
    best_win_r: float
    expectancy_r: float
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "evaluator_id": self.evaluator_id, "created_at": self.created_at,
            "total_plans": self.total_plans,
            "paper_open_count": self.paper_open_count,
            "tp1_count": self.tp1_count, "tp2_count": self.tp2_count,
            "tp3_count": self.tp3_count, "stop_count": self.stop_count,
            "time_stop_count": self.time_stop_count,
            "invalidated_count": self.invalidated_count,
            "win_rate": self.win_rate, "avg_pnl_r": self.avg_pnl_r,
            "median_pnl_r": self.median_pnl_r, "max_loss_r": self.max_loss_r,
            "best_win_r": self.best_win_r, "expectancy_r": self.expectancy_r,
            "final_verdict": self.final_verdict,
        }


def evaluate(positions: list[PaperPosition]) -> ReplayStats:
    total = len(positions)
    opened = [p for p in positions if p.status != "PLANNED"]
    closed = [p for p in positions if p.status in (
        "PAPER_CLOSED", "PAPER_STOPPED", "PAPER_TIME_STOPPED")]

    tp1 = sum(1 for p in positions if p.status in ("PAPER_TP1_HIT", "PAPER_TP2_HIT", "PAPER_CLOSED"))
    tp2 = sum(1 for p in positions if p.status in ("PAPER_TP2_HIT", "PAPER_CLOSED"))
    tp3 = sum(1 for p in positions if p.status == "PAPER_CLOSED")
    stops = sum(1 for p in positions if p.status == "PAPER_STOPPED")
    time_stops = sum(1 for p in positions if p.status == "PAPER_TIME_STOPPED")
    invalidated = sum(1 for p in positions if p.status == "PAPER_INVALIDATED")

    pnl_values = [p.paper_pnl_r for p in closed]
    wins = [v for v in pnl_values if v > 0]
    losses = [v for v in pnl_values if v < 0]

    win_rate = len(wins) / len(closed) * 100 if closed else 0.0
    avg_pnl = statistics.mean(pnl_values) if pnl_values else 0.0
    median_pnl = statistics.median(pnl_values) if pnl_values else 0.0
    max_loss = min(pnl_values) if pnl_values else 0.0
    best_win = max(pnl_values) if pnl_values else 0.0
    avg_win = statistics.mean(wins) if wins else 0.0
    avg_loss = statistics.mean(losses) if losses else 0.0
    win_prob = len(wins) / len(closed) if closed else 0.0
    expectancy = (win_prob * avg_win) + ((1 - win_prob) * avg_loss) if closed else 0.0

    return ReplayStats(
        evaluator_id=new_id("RE"),
        created_at=utc_now_iso(),
        total_plans=total,
        paper_open_count=len(opened),
        tp1_count=tp1, tp2_count=tp2, tp3_count=tp3,
        stop_count=stops, time_stop_count=time_stops,
        invalidated_count=invalidated,
        win_rate=round(win_rate, 2),
        avg_pnl_r=round(avg_pnl, 4),
        median_pnl_r=round(median_pnl, 4),
        max_loss_r=round(max_loss, 4),
        best_win_r=round(best_win, 4),
        expectancy_r=round(expectancy, 4),
        final_verdict=f"TRADE_PLAN_REPLAY_EVALUATOR_READY|TOTAL={total}|WIN_RATE={win_rate:.1f}%|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def write_stats(stats: ReplayStats, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats.to_dict(), indent=2), encoding="utf-8")


def render_report(stats: ReplayStats) -> str:
    lines = ["# Replay Evaluator", "",
        f"**evaluator_id={stats.evaluator_id}**", "",
        f"- total_plans: {stats.total_plans}",
        f"- paper_open_count: {stats.paper_open_count}",
        f"- tp1_count: {stats.tp1_count}",
        f"- tp2_count: {stats.tp2_count}",
        f"- tp3_count: {stats.tp3_count}",
        f"- stop_count: {stats.stop_count}",
        f"- time_stop_count: {stats.time_stop_count}",
        f"- invalidated_count: {stats.invalidated_count}",
        f"- win_rate: {stats.win_rate}%",
        f"- avg_pnl_r: {stats.avg_pnl_r}",
        f"- median_pnl_r: {stats.median_pnl_r}",
        f"- max_loss_r: {stats.max_loss_r}",
        f"- best_win_r: {stats.best_win_r}",
        f"- expectancy_r: {stats.expectancy_r}", "",
        "## Conclusion", "", stats.final_verdict, ""]
    return "\n".join(lines)
