"""Offline backtest scorecard — frozen dataclass + grading function.

Pure logic, no I/O, no network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence


# ---------------------------------------------------------------------------
# Quality gate defaults
# ---------------------------------------------------------------------------
_MIN_TRADES = 10
_MAX_DRAWDOWN_R = -5.0
_MIN_PROFIT_FACTOR = 1.0


@dataclass(frozen=True)
class BacktestScorecard:
    """Immutable scorecard for a single backtest run."""
    scorecard_id: str
    run_id: str
    grade: str  # PASS / WATCH / REJECT / INSUFFICIENT_SAMPLE
    metrics: Dict[str, Any]
    quality_gates: Dict[str, bool]
    reasons: tuple  # tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.scorecard_id:
            raise ValueError("scorecard_id must be non-empty")
        if not self.run_id:
            raise ValueError("run_id must be non-empty")
        valid_grades = {"PASS", "WATCH", "REJECT", "INSUFFICIENT_SAMPLE"}
        if self.grade not in valid_grades:
            raise ValueError(f"grade must be one of {valid_grades}, got {self.grade}")
        if not isinstance(self.reasons, tuple):
            raise ValueError("reasons must be a tuple")


def grade_run(
    run_result: Dict[str, Any],
    *,
    run_id: str = "",
    scorecard_id: str = "",
    min_trades: int = _MIN_TRADES,
    max_drawdown_r: float = _MAX_DRAWDOWN_R,
    min_profit_factor: float = _MIN_PROFIT_FACTOR,
) -> BacktestScorecard:
    """Grade a single backtest run based on quality gates.

    run_result must contain at least:
        trade_count, expectancy_r, max_drawdown_r, profit_factor

    Optional keys used:
        data_quality_clean (bool), split_coverage_full (bool)

    Returns BacktestScorecard with grade PASS / WATCH / REJECT / INSUFFICIENT_SAMPLE.
    """
    trade_count = run_result.get("trade_count", 0)
    expectancy_r = run_result.get("expectancy_r", 0.0)
    drawdown = run_result.get("max_drawdown_r", 0.0)
    pf = run_result.get("profit_factor", 0.0)
    data_quality_clean = run_result.get("data_quality_clean", True)
    split_coverage_full = run_result.get("split_coverage_full", True)

    gates: Dict[str, bool] = {
        "min_trades": trade_count >= min_trades,
        "positive_expectancy": expectancy_r > 0,
        "max_drawdown_r": drawdown > max_drawdown_r,
        "profit_factor": pf > min_profit_factor,
        "data_quality_clean": bool(data_quality_clean),
        "split_coverage_full": bool(split_coverage_full),
    }

    reasons: list[str] = []

    # --- Insufficient sample ---
    if not gates["min_trades"]:
        reasons.append(f"trade_count={trade_count} < min_trades={min_trades}")
        sc_id = scorecard_id or f"SC-{run_id or 'unknown'}"
        return BacktestScorecard(
            scorecard_id=sc_id,
            run_id=run_id or "unknown",
            grade="INSUFFICIENT_SAMPLE",
            metrics=run_result,
            quality_gates=gates,
            reasons=tuple(reasons),
        )

    # --- Hard rejects ---
    reject_reasons: list[str] = []
    if not gates["positive_expectancy"]:
        reject_reasons.append(f"expectancy_r={expectancy_r} <= 0")
    if not gates["max_drawdown_r"]:
        reject_reasons.append(f"max_drawdown_r={drawdown} <= {max_drawdown_r}")
    if not gates["profit_factor"]:
        reject_reasons.append(f"profit_factor={pf} <= {min_profit_factor}")

    if reject_reasons:
        reasons.extend(reject_reasons)
        sc_id = scorecard_id or f"SC-{run_id or 'unknown'}"
        return BacktestScorecard(
            scorecard_id=sc_id,
            run_id=run_id or "unknown",
            grade="REJECT",
            metrics=run_result,
            quality_gates=gates,
            reasons=tuple(reasons),
        )

    # --- Soft warnings -> WATCH ---
    watch_reasons: list[str] = []
    if not gates["data_quality_clean"]:
        watch_reasons.append("data_quality_issues_detected")
    if not gates["split_coverage_full"]:
        watch_reasons.append("incomplete_split_coverage")

    if watch_reasons:
        reasons.extend(watch_reasons)
        sc_id = scorecard_id or f"SC-{run_id or 'unknown'}"
        return BacktestScorecard(
            scorecard_id=sc_id,
            run_id=run_id or "unknown",
            grade="WATCH",
            metrics=run_result,
            quality_gates=gates,
            reasons=tuple(reasons),
        )

    # --- All gates pass ---
    sc_id = scorecard_id or f"SC-{run_id or 'unknown'}"
    return BacktestScorecard(
        scorecard_id=sc_id,
        run_id=run_id or "unknown",
        grade="PASS",
        metrics=run_result,
        quality_gates=gates,
        reasons=tuple(reasons),
    )
