"""Daily trade plan review report."""
from __future__ import annotations
import json, pathlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone

from src.trade_plan_engine.models import TradePlan, PaperPosition, new_id, utc_now_iso


@dataclass(frozen=True)
class DailyReview:
    review_id: str
    created_at: str
    report_date: str
    total_signals: int
    total_trade_plans: int
    grade_a_count: int
    grade_b_count: int
    grade_c_count: int
    rejected_count: int
    paper_open_count: int
    paper_closed_count: int
    tp_hit_count: int
    stop_count: int
    top_symbols: list[str]
    risk_notes: list[str]
    best_candidates: list[str]
    rejected_reasons: list[str]
    next_actions: list[str]
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id, "created_at": self.created_at,
            "report_date": self.report_date,
            "total_signals": self.total_signals,
            "total_trade_plans": self.total_trade_plans,
            "grade_a_count": self.grade_a_count,
            "grade_b_count": self.grade_b_count,
            "grade_c_count": self.grade_c_count,
            "rejected_count": self.rejected_count,
            "paper_open_count": self.paper_open_count,
            "paper_closed_count": self.paper_closed_count,
            "tp_hit_count": self.tp_hit_count,
            "stop_count": self.stop_count,
            "top_symbols": self.top_symbols,
            "risk_notes": self.risk_notes,
            "best_candidates": self.best_candidates,
            "rejected_reasons": self.rejected_reasons,
            "next_actions": self.next_actions,
            "final_verdict": self.final_verdict,
        }


def generate_review(
    signal_count: int,
    plans: list[TradePlan],
    positions: list[PaperPosition],
) -> DailyReview:
    grade_counter = Counter(p.plan_grade for p in plans)
    symbol_counter = Counter(p.symbol for p in plans)

    paper_open = sum(1 for p in positions if p.status == "PAPER_OPEN")
    paper_closed = sum(1 for p in positions if p.status in (
        "PAPER_CLOSED", "PAPER_STOPPED", "PAPER_TIME_STOPPED"))
    tp_hit = sum(1 for p in positions if p.status in (
        "PAPER_TP1_HIT", "PAPER_TP2_HIT", "PAPER_CLOSED"))
    stops = sum(1 for p in positions if p.status == "PAPER_STOPPED")

    risk_notes: list[str] = []
    high_risk = [p for p in plans if p.risk_pct > 6]
    if high_risk:
        risk_notes.append(f"{len(high_risk)} plans have risk > 6%")
    rejected = [p for p in plans if p.plan_grade == "REJECTED"]
    rejected_reasons = [p.explain for p in rejected[:5]]

    best = sorted([p for p in plans if p.plan_grade in ("A", "B")],
                  key=lambda p: p.risk_pct)[:5]
    best_candidates = [f"{p.symbol} {p.plan_grade} risk={p.risk_pct:.1f}%" for p in best]

    actions: list[str] = []
    if not plans:
        actions.append("No trade plans generated — verify scanner is running")
    if stops > tp_hit:
        actions.append("More stops than wins — review entry criteria")
    if not actions:
        actions.append("Continue monitoring")

    return DailyReview(
        review_id=new_id("DR"),
        created_at=utc_now_iso(),
        report_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        total_signals=signal_count,
        total_trade_plans=len(plans),
        grade_a_count=grade_counter.get("A", 0),
        grade_b_count=grade_counter.get("B", 0),
        grade_c_count=grade_counter.get("C", 0),
        rejected_count=grade_counter.get("REJECTED", 0),
        paper_open_count=paper_open,
        paper_closed_count=paper_closed,
        tp_hit_count=tp_hit,
        stop_count=stops,
        top_symbols=[s for s, _ in symbol_counter.most_common(5)],
        risk_notes=risk_notes,
        best_candidates=best_candidates,
        rejected_reasons=rejected_reasons,
        next_actions=actions,
        final_verdict=f"DAILY_TRADE_PLAN_REVIEW_READY|PLANS={len(plans)}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def write_review(review: DailyReview, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(review.to_dict(), indent=2), encoding="utf-8")


def render_report(review: DailyReview) -> str:
    lines = ["# Daily Trade Plan Review", "",
        f"**review_id={review.review_id}**",
        f"**date={review.report_date}**", "",
        f"- total_signals: {review.total_signals}",
        f"- total_trade_plans: {review.total_trade_plans}",
        f"- grade_a: {review.grade_a_count}",
        f"- grade_b: {review.grade_b_count}",
        f"- grade_c: {review.grade_c_count}",
        f"- rejected: {review.rejected_count}",
        f"- paper_open: {review.paper_open_count}",
        f"- paper_closed: {review.paper_closed_count}",
        f"- tp_hit: {review.tp_hit_count}",
        f"- stop: {review.stop_count}", "",
        "## Top Symbols", ""]
    for s in review.top_symbols:
        lines.append(f"- {s}")
    lines.extend(["", "## Best Candidates", ""])
    for b in review.best_candidates:
        lines.append(f"- {b}")
    lines.extend(["", "## Risk Notes", ""])
    for r in review.risk_notes:
        lines.append(f"- {r}")
    lines.extend(["", "## Next Actions", ""])
    for a in review.next_actions:
        lines.append(f"- {a}")
    lines.extend(["", "## Conclusion", "", review.final_verdict, ""])
    return "\n".join(lines)
