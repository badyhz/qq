"""Strategy scorecard — local quality rating, no network."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.paper_trading.performance_metrics import PerformanceMetrics


class Rating(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    REJECT = "REJECT"


@dataclass(frozen=True)
class Scorecard:
    win_rate_score: float
    profit_factor_score: float
    drawdown_score: float
    expectancy_score: float
    trade_count_score: float
    risk_penalty: float
    stability_score: float
    final_score: float
    rating: Rating


def score_strategy(metrics: PerformanceMetrics, equity: float = 100000.0) -> Scorecard:
    """Score a strategy based on performance metrics.

    Rules:
    - Sample too small → downgrade
    - All wins but small sample → max B
    - Profit factor inf but few trades → downgrade
    - High drawdown → downgrade
    - Negative expectancy → C/D/REJECT
    """
    # Trade count score (0-20)
    if metrics.total_trades == 0:
        return Scorecard(
            win_rate_score=0, profit_factor_score=0, drawdown_score=0,
            expectancy_score=0, trade_count_score=0, risk_penalty=0,
            stability_score=0, final_score=0, rating=Rating.REJECT,
        )

    tc = metrics.total_trades
    if tc >= 20:
        trade_count_score = 20
    elif tc >= 10:
        trade_count_score = 15
    elif tc >= 5:
        trade_count_score = 10
    else:
        trade_count_score = 5

    # Win rate score (0-20)
    wr = metrics.win_rate
    if wr >= 0.6:
        win_rate_score = 20
    elif wr >= 0.5:
        win_rate_score = 15
    elif wr >= 0.4:
        win_rate_score = 10
    elif wr >= 0.3:
        win_rate_score = 5
    else:
        win_rate_score = 0

    # Profit factor score (0-20)
    pf = metrics.profit_factor
    if pf == float("inf"):
        if tc >= 10:
            profit_factor_score = 20
        else:
            profit_factor_score = 12  # downgrade for small sample
    elif pf >= 3.0:
        profit_factor_score = 20
    elif pf >= 2.0:
        profit_factor_score = 15
    elif pf >= 1.5:
        profit_factor_score = 10
    elif pf >= 1.0:
        profit_factor_score = 5
    else:
        profit_factor_score = 0

    # Drawdown score (0-20, lower DD is better)
    dd_pct = metrics.max_drawdown / equity * 100 if equity > 0 else 0
    if dd_pct <= 1:
        drawdown_score = 20
    elif dd_pct <= 3:
        drawdown_score = 15
    elif dd_pct <= 5:
        drawdown_score = 10
    elif dd_pct <= 10:
        drawdown_score = 5
    else:
        drawdown_score = 0

    # Expectancy score (0-20)
    exp = metrics.expectancy
    if exp > 200:
        expectancy_score = 20
    elif exp > 100:
        expectancy_score = 15
    elif exp > 0:
        expectancy_score = 10
    elif exp > -50:
        expectancy_score = 3
    else:
        expectancy_score = 0

    # Risk penalty (0 to -15)
    risk_penalty = 0.0
    if metrics.max_consecutive_losses >= 5:
        risk_penalty -= 10
    elif metrics.max_consecutive_losses >= 3:
        risk_penalty -= 5
    if dd_pct > 10:
        risk_penalty -= 5

    # Stability score (0-10)
    stability_score = 0.0
    if metrics.avg_rr_actual > 1.0:
        stability_score += 5
    elif metrics.avg_rr_actual > 0.5:
        stability_score += 3
    if metrics.total_trades >= 10 and metrics.win_rate >= 0.5:
        stability_score += 5

    # Final score
    final_score = (
        win_rate_score + profit_factor_score + drawdown_score +
        expectancy_score + trade_count_score + risk_penalty + stability_score
    )

    # Rating
    small_sample = tc < 5
    all_wins = metrics.losers == 0 and metrics.winners > 0

    if metrics.total_trades == 0:
        rating = Rating.REJECT
    elif exp < 0 and tc >= 5:
        rating = Rating.D if final_score >= 20 else Rating.REJECT
    elif small_sample:
        if final_score >= 50:
            rating = Rating.B  # cap at B for small sample
        elif final_score >= 30:
            rating = Rating.C
        else:
            rating = Rating.D
    elif all_wins and small_sample:
        rating = Rating.B  # cap at B
    elif final_score >= 75:
        rating = Rating.A
    elif final_score >= 55:
        rating = Rating.B
    elif final_score >= 35:
        rating = Rating.C
    elif final_score >= 20:
        rating = Rating.D
    else:
        rating = Rating.REJECT

    return Scorecard(
        win_rate_score=win_rate_score,
        profit_factor_score=profit_factor_score,
        drawdown_score=drawdown_score,
        expectancy_score=expectancy_score,
        trade_count_score=trade_count_score,
        risk_penalty=risk_penalty,
        stability_score=stability_score,
        final_score=final_score,
        rating=rating,
    )
