"""Portfolio research aggregation — aggregate strategy results at portfolio level.

Offline research only. Does not imply executable portfolio allocation.
No network, no exchange, no live, no submit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class PortfolioAggregateResult:
    """Portfolio-level aggregation of strategy results."""
    portfolio_id: str
    included_strategy_ids: Tuple[str, ...]
    included_symbols: Tuple[str, ...]
    included_timeframes: Tuple[str, ...]
    total_trades: int
    aggregate_expectancy_r: float
    aggregate_win_rate: float
    aggregate_profit_factor: float
    max_drawdown_approx: float
    equity_curve_approx: Tuple[float, ...]
    exposure_summary: Dict[str, Any]
    drawdown_summary: Dict[str, Any]
    trade_overlap_summary: Dict[str, Any]
    warnings: Tuple[str, ...]


def aggregate_portfolio(
    results: list,
    portfolio_id: str = "portfolio_research_001",
) -> PortfolioAggregateResult:
    """Aggregate run results into portfolio-level metrics.

    Research approximation only. Not executable portfolio allocation.
    """
    if not results:
        return PortfolioAggregateResult(
            portfolio_id=portfolio_id,
            included_strategy_ids=(),
            included_symbols=(),
            included_timeframes=(),
            total_trades=0,
            aggregate_expectancy_r=0.0,
            aggregate_win_rate=0.0,
            aggregate_profit_factor=0.0,
            max_drawdown_approx=0.0,
            equity_curve_approx=(),
            exposure_summary={},
            drawdown_summary={},
            trade_overlap_summary={},
            warnings=("NO_RESULTS",),
        )

    strategy_ids = sorted(set(r.strategy_id for r in results))
    symbols = sorted(set(r.symbol for r in results))
    timeframes = sorted(set(r.timeframe for r in results))
    total_trades = sum(r.trade_count for r in results)

    # Aggregate metrics (simple averages for research)
    n = len(results)
    avg_expectancy = sum(r.expectancy_r for r in results) / n
    avg_win_rate = sum(r.win_rate for r in results) / n
    avg_pf = sum(r.profit_factor for r in results) / n
    max_dd = max(r.max_drawdown for r in results) if results else 0.0

    # Simple equity curve approximation
    equity = [1.0]
    for r in sorted(results, key=lambda x: x.matrix_row_id):
        equity.append(equity[-1] * (1.0 + r.avg_return))
    equity_tuple = tuple(round(e, 6) for e in equity)

    # Exposure by symbol
    exposure_by_symbol: Dict[str, int] = {}
    for r in results:
        exposure_by_symbol[r.symbol] = exposure_by_symbol.get(r.symbol, 0) + r.trade_count

    # Drawdown contribution
    dd_by_strategy: Dict[str, float] = {}
    for r in results:
        cur = dd_by_strategy.get(r.strategy_id, 0.0)
        dd_by_strategy[r.strategy_id] = max(cur, r.max_drawdown)

    warnings: List[str] = []
    if total_trades < 10:
        warnings.append("LOW_TOTAL_TRADES")

    return PortfolioAggregateResult(
        portfolio_id=portfolio_id,
        included_strategy_ids=tuple(strategy_ids),
        included_symbols=tuple(symbols),
        included_timeframes=tuple(timeframes),
        total_trades=total_trades,
        aggregate_expectancy_r=round(avg_expectancy, 6),
        aggregate_win_rate=round(avg_win_rate, 4),
        aggregate_profit_factor=round(avg_pf, 4),
        max_drawdown_approx=round(max_dd, 6),
        equity_curve_approx=equity_tuple,
        exposure_summary={"by_symbol": exposure_by_symbol},
        drawdown_summary={"by_strategy": dd_by_strategy},
        trade_overlap_summary={},
        warnings=tuple(warnings),
    )


def portfolio_to_dict(result: PortfolioAggregateResult) -> Dict[str, Any]:
    """Serialize to dict."""
    return {
        "portfolio_id": result.portfolio_id,
        "included_strategy_ids": list(result.included_strategy_ids),
        "included_symbols": list(result.included_symbols),
        "included_timeframes": list(result.included_timeframes),
        "total_trades": result.total_trades,
        "aggregate_expectancy_r": result.aggregate_expectancy_r,
        "aggregate_win_rate": result.aggregate_win_rate,
        "aggregate_profit_factor": result.aggregate_profit_factor,
        "max_drawdown_approx": result.max_drawdown_approx,
        "equity_curve_approx": list(result.equity_curve_approx),
        "exposure_summary": result.exposure_summary,
        "drawdown_summary": result.drawdown_summary,
        "trade_overlap_summary": result.trade_overlap_summary,
        "warnings": list(result.warnings),
    }


def portfolio_to_json(result: PortfolioAggregateResult, indent: int = 2) -> str:
    """Serialize to JSON."""
    return json.dumps(portfolio_to_dict(result), sort_keys=True, indent=indent)
