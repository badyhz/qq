"""Out-of-sample scoring — train/validation/test stability scoring.

Computes degradation, overfit, stability penalty, sample size warnings.
Pure functions, no network, no exchange.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class OOSScore:
    """Out-of-sample score for a strategy run."""
    strategy_id: str
    parameter_set_id: str
    symbol: str
    timeframe: str
    train_score: float
    validation_score: float
    test_score: float
    stability_penalty: float
    overfit_flag: bool
    degradation_flag: bool
    sample_size_warning: bool
    promotion_score: float


def compute_oos_score(
    strategy_id: str,
    parameter_set_id: str,
    symbol: str,
    timeframe: str,
    train_score: float,
    validation_score: float,
    test_score: float,
    train_trades: int = 0,
    validation_trades: int = 0,
    test_trades: int = 0,
    min_trades_per_split: int = 5,
    degradation_threshold: float = 0.3,
    overfit_threshold: float = 0.5,
) -> OOSScore:
    """Compute out-of-sample score.

    Pure function. Deterministic.
    """
    # Sample size warning
    sample_size_warning = (
        train_trades < min_trades_per_split
        or validation_trades < min_trades_per_split
        or test_trades < min_trades_per_split
    )

    # Degradation: validation much worse than train, or test much worse than validation
    degradation = False
    if train_score > 0:
        val_drop = (train_score - validation_score) / train_score
        if val_drop > degradation_threshold:
            degradation = True
    if validation_score > 0:
        test_drop = (validation_score - test_score) / validation_score
        if test_drop > degradation_threshold:
            degradation = True

    # Overfit: train high but validation/test weak
    overfit = False
    if train_score > 0.7 and validation_score < train_score * (1 - overfit_threshold):
        overfit = True
    if train_score > 0.7 and test_score < train_score * (1 - overfit_threshold):
        overfit = True

    # Stability penalty
    scores = [s for s in [train_score, validation_score, test_score] if s > 0]
    if len(scores) >= 2:
        mean_s = sum(scores) / len(scores)
        variance = sum((s - mean_s) ** 2 for s in scores) / len(scores)
        stability_penalty = round(min(1.0, variance * 4), 4)
    else:
        stability_penalty = 0.0

    # Promotion score: weighted average penalized
    base_score = (train_score * 0.4 + validation_score * 0.3 + test_score * 0.3)
    promotion_score = max(0.0, base_score - stability_penalty * 0.3)
    if overfit:
        promotion_score *= 0.5
    if degradation:
        promotion_score *= 0.7
    if sample_size_warning:
        promotion_score *= 0.8

    return OOSScore(
        strategy_id=strategy_id,
        parameter_set_id=parameter_set_id,
        symbol=symbol,
        timeframe=timeframe,
        train_score=round(train_score, 6),
        validation_score=round(validation_score, 6),
        test_score=round(test_score, 6),
        stability_penalty=stability_penalty,
        overfit_flag=overfit,
        degradation_flag=degradation,
        sample_size_warning=sample_size_warning,
        promotion_score=round(promotion_score, 6),
    )


def oos_score_to_dict(score: OOSScore) -> Dict[str, Any]:
    """Serialize to dict."""
    return {
        "strategy_id": score.strategy_id,
        "parameter_set_id": score.parameter_set_id,
        "symbol": score.symbol,
        "timeframe": score.timeframe,
        "train_score": score.train_score,
        "validation_score": score.validation_score,
        "test_score": score.test_score,
        "stability_penalty": score.stability_penalty,
        "overfit_flag": score.overfit_flag,
        "degradation_flag": score.degradation_flag,
        "sample_size_warning": score.sample_size_warning,
        "promotion_score": score.promotion_score,
    }
