"""Candidate ranker — score and prioritize review candidates. No network."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    REJECT = "REJECT"


@dataclass(frozen=True)
class RankedCandidate:
    review_id: str
    rank: int
    priority: Priority
    rank_score: float
    reason_codes: List[str]
    human_summary: str
    # Passthrough fields
    symbol: str
    strategy_name: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    score: float
    rating: str
    risk_summary: str
    operator_status: str
    source_run_id: str
    safety_flags: List[str]


def rank_candidate(
    review_id: str,
    symbol: str,
    strategy_name: str,
    side: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    score: float,
    rating: str,
    risk_summary: str = "",
    operator_status: str = "PENDING_REVIEW",
    source_run_id: str = "",
    safety_flags: Optional[List[str]] = None,
    trade_count: int = 0,
    max_drawdown: float = 0.0,
    profit_factor: float = 0.0,
    duplicate_symbol_count: int = 0,
) -> RankedCandidate:
    """Rank a single candidate and assign priority."""
    rank_score = 0.0
    reasons: List[str] = []

    # Base score from strategy score (0-100)
    rank_score += score * 0.4

    # Rating bonus
    rating_bonus = {"A": 25, "B": 15, "C": 5, "D": -10, "REJECT": -30}
    rb = rating_bonus.get(rating, 0)
    rank_score += rb
    if rating in ("A", "B"):
        reasons.append(f"rating_{rating.lower()}")
    elif rating == "C":
        reasons.append("rating_c_marginal")
    else:
        reasons.append(f"rating_{rating.lower()}_weak")

    # RR ratio
    risk = abs(entry_price - stop_loss) if stop_loss != entry_price else 1
    reward = abs(take_profit - entry_price)
    rr = reward / risk if risk > 0 else 0
    if rr >= 2.0:
        rank_score += 10
        reasons.append("good_rr")
    elif rr >= 1.5:
        rank_score += 5
        reasons.append("acceptable_rr")
    else:
        rank_score -= 10
        reasons.append("low_rr")

    # Small sample penalty
    if trade_count < 5:
        rank_score -= 10
        reasons.append("small_sample")
    elif trade_count < 10:
        rank_score -= 5
        reasons.append("limited_sample")

    # High drawdown penalty
    if max_drawdown > 10:
        rank_score -= 15
        reasons.append("high_drawdown")
    elif max_drawdown > 5:
        rank_score -= 5
        reasons.append("moderate_drawdown")

    # Profit factor
    if profit_factor >= 2.0:
        rank_score += 5
        reasons.append("strong_profit_factor")
    elif profit_factor < 1.0 and profit_factor > 0:
        rank_score -= 10
        reasons.append("weak_profit_factor")

    # Duplicate symbol penalty
    if duplicate_symbol_count > 0:
        rank_score -= 8 * duplicate_symbol_count
        reasons.append("duplicate_symbol")

    # Determine priority
    if rating in ("D", "REJECT"):
        priority = Priority.REJECT
    elif rank_score >= 60:
        priority = Priority.HIGH
    elif rank_score >= 40:
        priority = Priority.MEDIUM
    else:
        priority = Priority.LOW

    # Human summary
    summary = _build_summary(symbol, side, rating, score, priority, reasons)

    return RankedCandidate(
        review_id=review_id,
        rank=0,  # Set by caller after sorting
        priority=priority,
        rank_score=round(rank_score, 2),
        reason_codes=reasons,
        human_summary=summary,
        symbol=symbol,
        strategy_name=strategy_name,
        side=side,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        score=score,
        rating=rating,
        risk_summary=risk_summary,
        operator_status=operator_status,
        source_run_id=source_run_id,
        safety_flags=safety_flags or ["NO_REAL_ORDER", "PAPER_ONLY"],
    )


def rank_candidates(candidates: list, **kwargs) -> List[RankedCandidate]:
    """Rank a list of review candidates. Returns sorted by rank_score descending."""
    ranked = []
    for c in candidates:
        extra = {}
        if hasattr(c, "__dict__"):
            extra = {k: v for k, v in c.__dict__.items() if k not in c.__dataclass_fields__}
        rc = rank_candidate(
            review_id=c.review_id,
            symbol=c.symbol,
            strategy_name=c.strategy_name,
            side=c.side,
            entry_price=c.entry_price,
            stop_loss=c.stop_loss,
            take_profit=c.take_profit,
            score=c.score,
            rating=c.rating,
            risk_summary=c.risk_summary,
            operator_status=c.operator_status,
            source_run_id=c.source_run_id,
            safety_flags=c.safety_flags if hasattr(c, "safety_flags") else None,
            **extra,
            **kwargs,
        )
        ranked.append(rc)

    ranked.sort(key=lambda r: r.rank_score, reverse=True)
    # Assign ranks
    result = []
    for i, r in enumerate(ranked):
        result.append(RankedCandidate(
            review_id=r.review_id, rank=i + 1, priority=r.priority,
            rank_score=r.rank_score, reason_codes=r.reason_codes,
            human_summary=r.human_summary, symbol=r.symbol,
            strategy_name=r.strategy_name, side=r.side,
            entry_price=r.entry_price, stop_loss=r.stop_loss,
            take_profit=r.take_profit, score=r.score, rating=r.rating,
            risk_summary=r.risk_summary, operator_status=r.operator_status,
            source_run_id=r.source_run_id, safety_flags=r.safety_flags,
        ))
    return result


def _build_summary(symbol: str, side: str, rating: str, score: float,
                   priority: Priority, reasons: List[str]) -> str:
    parts = [f"{symbol} {side} rated {rating} (score {score:.0f})"]
    if priority == Priority.HIGH:
        parts.append("— HIGH priority, strong candidate")
    elif priority == Priority.MEDIUM:
        parts.append("— MEDIUM priority, worth watching")
    elif priority == Priority.LOW:
        parts.append("— LOW priority, marginal")
    else:
        parts.append("— REJECTED, does not meet criteria")

    key_reasons = [r for r in reasons if r.startswith(("rating_", "small_sample", "high_drawdown", "duplicate_symbol"))]
    if key_reasons:
        parts.append(f"({', '.join(key_reasons)})")
    return " ".join(parts)
