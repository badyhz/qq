"""Strategy research promotion policy — assign promotion/rejection status.

Statuses: PROMOTE_TO_NEXT_RESEARCH_ROUND, WATCH_MORE_DATA, REJECT_OVERFIT,
REJECT_DRAWDOWN, HUMAN_REVIEW_REQUIRED, KEEP_HOLD.

All statuses retain release_hold = HOLD.
No network, no exchange, no live, no submit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.strategy_research_oos_scoring import OOSScore


PROMOTION_STATUSES = frozenset({
    "PROMOTE_TO_NEXT_RESEARCH_ROUND",
    "WATCH_MORE_DATA",
    "REJECT_OVERFIT",
    "REJECT_DRAWDOWN",
    "HUMAN_REVIEW_REQUIRED",
    "KEEP_HOLD",
})


@dataclass(frozen=True)
class PromotionRecommendation:
    """A promotion recommendation for a strategy run."""
    recommendation_id: str
    strategy_id: str
    parameter_set_id: str
    symbol: str
    timeframe: str
    status: str
    reasons: Tuple[str, ...]
    blocking_risks: Tuple[str, ...]
    release_hold: str = "HOLD"
    human_review_required: bool = False


def evaluate_promotion(
    oos_score: OOSScore,
    max_drawdown: float = 0.0,
    max_drawdown_limit: float = 0.15,
    min_promotion_score: float = 0.3,
) -> PromotionRecommendation:
    """Evaluate promotion status from OOS score and metrics.

    Pure function. Always retains release_hold = HOLD.
    """
    reasons: List[str] = []
    blocking_risks: List[str] = []
    human_review = False

    # Check rejection conditions first
    if oos_score.overfit_flag:
        reasons.append("overfit detected: train high, validation/test weak")
        blocking_risks.append("OVERFIT")
        status = "REJECT_OVERFIT"
    elif oos_score.degradation_flag:
        reasons.append("out-of-sample degradation detected")
        blocking_risks.append("DEGRADATION")
        status = "REJECT_OVERFIT"
    elif max_drawdown > max_drawdown_limit:
        reasons.append(f"max drawdown {max_drawdown:.4f} exceeds limit {max_drawdown_limit:.4f}")
        blocking_risks.append("DRAWDOWN")
        status = "REJECT_DRAWDOWN"
    elif oos_score.sample_size_warning:
        reasons.append("insufficient sample size for robust conclusion")
        status = "WATCH_MORE_DATA"
    elif oos_score.promotion_score < min_promotion_score:
        reasons.append(f"promotion score {oos_score.promotion_score:.4f} below threshold {min_promotion_score:.4f}")
        status = "WATCH_MORE_DATA"
    elif oos_score.stability_penalty > 0.5:
        reasons.append("high stability penalty across splits")
        status = "HUMAN_REVIEW_REQUIRED"
        human_review = True
    else:
        reasons.append("all checks passed for research continuation")
        status = "PROMOTE_TO_NEXT_RESEARCH_ROUND"

    rec_id = f"promo_{oos_score.strategy_id}_{oos_score.parameter_set_id}_{oos_score.symbol}_{oos_score.timeframe}"

    return PromotionRecommendation(
        recommendation_id=rec_id,
        strategy_id=oos_score.strategy_id,
        parameter_set_id=oos_score.parameter_set_id,
        symbol=oos_score.symbol,
        timeframe=oos_score.timeframe,
        status=status,
        reasons=tuple(reasons),
        blocking_risks=tuple(blocking_risks),
        release_hold="HOLD",
        human_review_required=human_review,
    )


def promotion_to_dict(rec: PromotionRecommendation) -> Dict[str, Any]:
    """Serialize to dict."""
    return {
        "recommendation_id": rec.recommendation_id,
        "strategy_id": rec.strategy_id,
        "parameter_set_id": rec.parameter_set_id,
        "symbol": rec.symbol,
        "timeframe": rec.timeframe,
        "status": rec.status,
        "reasons": list(rec.reasons),
        "blocking_risks": list(rec.blocking_risks),
        "release_hold": rec.release_hold,
        "human_review_required": rec.human_review_required,
    }
