"""Paper performance metrics — strategy scorecard from clean positions only.

No orders, no accounts, no secrets. Pure statistics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SAMPLE_STATUS_INSUFFICIENT = "INSUFFICIENT_CLOSED_SAMPLE"
SAMPLE_STATUS_LOW = "LOW_SAMPLE_SIZE"
SAMPLE_STATUS_EVALUABLE = "EVALUABLE"

STRATEGY_STATUS_OBSERVE_ONLY = "OBSERVE_ONLY"
STRATEGY_STATUS_OBSERVE_MORE = "OBSERVE_MORE"
STRATEGY_STATUS_CANDIDATE_KEEP = "CANDIDATE_KEEP"
STRATEGY_STATUS_CANDIDATE_DISABLE = "CANDIDATE_DISABLE_OR_REDUCE_WEIGHT"

CLOSED_STATUSES = {"TAKE_PROFIT_HIT", "STOP_LOSS_HIT", "TIMEOUT_EXIT"}


@dataclass(frozen=True)
class GlobalMetrics:
    total_positions: int
    clean_positions: int
    excluded_positions: int
    open_positions: int
    closed_positions: int
    take_profit_hit: int
    stop_loss_hit: int
    timeout_exit: int
    realized_pnl: float
    unrealized_pnl: float
    avg_r_multiple: float
    win_rate: float
    loss_rate: float
    profit_factor: float
    expectancy_r: float
    max_single_loss_r: float
    max_single_win_r: float
    sample_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_positions": self.total_positions,
            "clean_positions": self.clean_positions,
            "excluded_positions": self.excluded_positions,
            "open_positions": self.open_positions,
            "closed_positions": self.closed_positions,
            "take_profit_hit": self.take_profit_hit,
            "stop_loss_hit": self.stop_loss_hit,
            "timeout_exit": self.timeout_exit,
            "realized_pnl": round(self.realized_pnl, 8),
            "unrealized_pnl": round(self.unrealized_pnl, 8),
            "avg_r_multiple": round(self.avg_r_multiple, 4),
            "win_rate": round(self.win_rate, 4),
            "loss_rate": round(self.loss_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
            "expectancy_r": round(self.expectancy_r, 4),
            "max_single_loss_r": round(self.max_single_loss_r, 4),
            "max_single_win_r": round(self.max_single_win_r, 4),
            "sample_status": self.sample_status,
        }


@dataclass(frozen=True)
class StrategyScorecard:
    strategy_id: str
    strategy_type: str
    symbol_count: int
    position_count: int
    open_count: int
    closed_count: int
    tp_count: int
    sl_count: int
    timeout_count: int
    realized_pnl: float
    unrealized_pnl: float
    avg_r_multiple: float
    win_rate: float
    profit_factor: float
    expectancy_r: float
    sample_status: str
    strategy_score: float
    strategy_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_type": self.strategy_type,
            "symbol_count": self.symbol_count,
            "position_count": self.position_count,
            "open_count": self.open_count,
            "closed_count": self.closed_count,
            "tp_count": self.tp_count,
            "sl_count": self.sl_count,
            "timeout_count": self.timeout_count,
            "realized_pnl": round(self.realized_pnl, 8),
            "unrealized_pnl": round(self.unrealized_pnl, 8),
            "avg_r_multiple": round(self.avg_r_multiple, 4),
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
            "expectancy_r": round(self.expectancy_r, 4),
            "sample_status": self.sample_status,
            "strategy_score": round(self.strategy_score, 4),
            "strategy_status": self.strategy_status,
        }


@dataclass(frozen=True)
class PerformanceScorecard:
    date: str
    global_metrics: GlobalMetrics
    strategy_scorecards: list[StrategyScorecard]
    clean_positions: list[dict[str, Any]]
    excluded_positions: list[dict[str, Any]]
    safety_flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "global_metrics": self.global_metrics.to_dict(),
            "strategy_scorecards": [s.to_dict() for s in self.strategy_scorecards],
            "clean_position_count": len(self.clean_positions),
            "excluded_position_count": len(self.excluded_positions),
            "safety_flags": list(self.safety_flags),
        }


PERFORMANCE_SAFETY_FLAGS = [
    "PAPER_ONLY",
    "SHADOW_ONLY",
    "NO_ORDER",
    "NO_REAL_ORDER",
    "NO_ACCOUNT",
    "NO_SECRET",
    "NO_TESTNET",
    "NO_LIVE",
    "READONLY_METADATA_ONLY",
    "STATS_FROM_CLEAN_POSITIONS_ONLY",
]


def compute_performance(
    positions: list[dict[str, Any]],
    date_str: str,
) -> PerformanceScorecard:
    """Compute performance metrics from clean positions only."""
    clean = [p for p in positions if not p.get("excluded_from_performance_stats", False)]
    excluded = [p for p in positions if p.get("excluded_from_performance_stats", False)]

    global_metrics = _compute_global(clean, excluded)
    strategy_scorecards = _compute_strategies(clean)

    return PerformanceScorecard(
        date=date_str,
        global_metrics=global_metrics,
        strategy_scorecards=strategy_scorecards,
        clean_positions=clean,
        excluded_positions=excluded,
        safety_flags=list(PERFORMANCE_SAFETY_FLAGS),
    )


def _compute_global(
    clean: list[dict[str, Any]],
    excluded: list[dict[str, Any]],
) -> GlobalMetrics:
    total = len(clean) + len(excluded)
    open_count = sum(1 for p in clean if p.get("status") == "OPEN")
    tp = sum(1 for p in clean if p.get("status") == "TAKE_PROFIT_HIT")
    sl = sum(1 for p in clean if p.get("status") == "STOP_LOSS_HIT")
    timeout = sum(1 for p in clean if p.get("status") == "TIMEOUT_EXIT")
    closed = tp + sl + timeout

    realized = sum(p.get("realized_pnl", 0) for p in clean)
    unrealized = sum(p.get("unrealized_pnl", 0) for p in clean)

    closed_with_r = [p for p in clean if p.get("status") in CLOSED_STATUSES]
    r_values = [p.get("r_multiple", 0) for p in closed_with_r]
    avg_r = sum(r_values) / len(r_values) if r_values else 0.0

    win_rate = tp / closed if closed > 0 else 0.0
    loss_rate = (sl + timeout) / closed if closed > 0 else 0.0

    gross_profit = sum(p.get("realized_pnl", 0) for p in clean if p.get("realized_pnl", 0) > 0)
    gross_loss = abs(sum(p.get("realized_pnl", 0) for p in clean if p.get("realized_pnl", 0) < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    expectancy_r = avg_r

    max_loss_r = min(r_values) if r_values else 0.0
    max_win_r = max(r_values) if r_values else 0.0

    sample_status = _determine_sample_status(closed)

    return GlobalMetrics(
        total_positions=total,
        clean_positions=len(clean),
        excluded_positions=len(excluded),
        open_positions=open_count,
        closed_positions=closed,
        take_profit_hit=tp,
        stop_loss_hit=sl,
        timeout_exit=timeout,
        realized_pnl=realized,
        unrealized_pnl=unrealized,
        avg_r_multiple=avg_r,
        win_rate=win_rate,
        loss_rate=loss_rate,
        profit_factor=profit_factor,
        expectancy_r=expectancy_r,
        max_single_loss_r=max_loss_r,
        max_single_win_r=max_win_r,
        sample_status=sample_status,
    )


def _compute_strategies(clean: list[dict[str, Any]]) -> list[StrategyScorecard]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for p in clean:
        sid = p.get("strategy_id", "unknown")
        grouped.setdefault(sid, []).append(p)

    scorecards = []
    for sid, positions in sorted(grouped.items()):
        scorecards.append(_build_strategy_scorecard(sid, positions))
    return scorecards


def _build_strategy_scorecard(
    strategy_id: str,
    positions: list[dict[str, Any]],
) -> StrategyScorecard:
    stype = positions[0].get("strategy_type", strategy_id)
    symbols = {p.get("symbol", "") for p in positions}
    open_count = sum(1 for p in positions if p.get("status") == "OPEN")
    tp = sum(1 for p in positions if p.get("status") == "TAKE_PROFIT_HIT")
    sl = sum(1 for p in positions if p.get("status") == "STOP_LOSS_HIT")
    timeout = sum(1 for p in positions if p.get("status") == "TIMEOUT_EXIT")
    closed = tp + sl + timeout

    realized = sum(p.get("realized_pnl", 0) for p in positions)
    unrealized = sum(p.get("unrealized_pnl", 0) for p in positions)

    closed_with_r = [p for p in positions if p.get("status") in CLOSED_STATUSES]
    r_values = [p.get("r_multiple", 0) for p in closed_with_r]
    avg_r = sum(r_values) / len(r_values) if r_values else 0.0

    win_rate = tp / closed if closed > 0 else 0.0

    gross_profit = sum(p.get("realized_pnl", 0) for p in positions if p.get("realized_pnl", 0) > 0)
    gross_loss = abs(sum(p.get("realized_pnl", 0) for p in positions if p.get("realized_pnl", 0) < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    expectancy_r = avg_r
    sample_status = _determine_sample_status(closed)
    strategy_score = _compute_strategy_score(expectancy_r, profit_factor, closed)
    strategy_status = _determine_strategy_status(sample_status, expectancy_r, profit_factor)

    return StrategyScorecard(
        strategy_id=strategy_id,
        strategy_type=stype,
        symbol_count=len(symbols),
        position_count=len(positions),
        open_count=open_count,
        closed_count=closed,
        tp_count=tp,
        sl_count=sl,
        timeout_count=timeout,
        realized_pnl=realized,
        unrealized_pnl=unrealized,
        avg_r_multiple=avg_r,
        win_rate=win_rate,
        profit_factor=profit_factor,
        expectancy_r=expectancy_r,
        sample_status=sample_status,
        strategy_score=strategy_score,
        strategy_status=strategy_status,
    )


def _determine_sample_status(closed_count: int) -> str:
    if closed_count == 0:
        return SAMPLE_STATUS_INSUFFICIENT
    if closed_count < 10:
        return SAMPLE_STATUS_LOW
    return SAMPLE_STATUS_EVALUABLE


def _determine_strategy_status(
    sample_status: str,
    expectancy_r: float,
    profit_factor: float,
) -> str:
    if sample_status == SAMPLE_STATUS_INSUFFICIENT:
        return STRATEGY_STATUS_OBSERVE_ONLY
    if sample_status == SAMPLE_STATUS_LOW:
        return STRATEGY_STATUS_OBSERVE_MORE
    if expectancy_r > 0 and profit_factor >= 1.2:
        return STRATEGY_STATUS_CANDIDATE_KEEP
    return STRATEGY_STATUS_CANDIDATE_DISABLE


def _compute_strategy_score(
    expectancy_r: float,
    profit_factor: float,
    closed_count: int,
) -> float:
    if closed_count == 0:
        return 0.0
    base = expectancy_r * min(closed_count / 10.0, 1.0)
    pf_bonus = min(profit_factor / 2.0, 1.0) if profit_factor > 0 else 0.0
    return round(base + pf_bonus, 4)
