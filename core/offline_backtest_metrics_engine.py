"""Offline backtest metrics engine — pure functions, no I/O.

Computes per-run and aggregate metrics from trade outcome dicts.
"""
from __future__ import annotations

import math
import statistics
from typing import Any, Dict, List, Sequence


def _safe_median(values: Sequence[float]) -> float:
    """Return median of values, or 0.0 if empty."""
    if not values:
        return 0.0
    return float(statistics.median(values))


def _safe_mean(values: Sequence[float]) -> float:
    """Return mean of values, or 0.0 if empty."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def compute_max_drawdown_r(equity_curve: Sequence[float]) -> float:
    """Compute max drawdown in R-multiples from an equity curve.

    Returns a negative number (or 0.0 if no drawdown).
    """
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = val - peak
        if dd < max_dd:
            max_dd = dd
    return max_dd


def compute_profit_factor(gross_wins: float, gross_losses: float) -> float:
    """Profit factor = gross_wins / abs(gross_losses). Returns 0.0 if no losses."""
    if gross_losses == 0.0:
        return 0.0 if gross_wins == 0.0 else float("inf")
    return abs(gross_wins / gross_losses)


def compute_run_metrics(trades: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute all metrics for a single backtest run.

    Each trade dict must have keys:
        trade_id, signal_id, entry_bar_index, exit_bar_index,
        entry_price, exit_price, exit_reason, realized_r,
        gross_pnl, fees, slippage_cost, net_pnl,
        mfe_r, mae_r, hold_bars

    Returns dict with:
        trade_count, win_rate, expectancy_r, avg_r, median_r,
        max_drawdown_r, profit_factor, avg_mfe_r, avg_mae_r,
        exposure_bars, avg_hold_bars, quality_adjusted_score,
        sample_adequacy_score
    """
    trade_count = len(trades)
    if trade_count == 0:
        return {
            "trade_count": 0,
            "win_rate": 0.0,
            "expectancy_r": 0.0,
            "avg_r": 0.0,
            "median_r": 0.0,
            "max_drawdown_r": 0.0,
            "profit_factor": 0.0,
            "avg_mfe_r": 0.0,
            "avg_mae_r": 0.0,
            "exposure_bars": 0,
            "avg_hold_bars": 0.0,
            "quality_adjusted_score": 0.0,
            "sample_adequacy_score": 0.0,
        }

    realized_rs = [float(t["realized_r"]) for t in trades]
    mfes = [float(t["mfe_r"]) for t in trades]
    maes = [float(t["mae_r"]) for t in trades]
    hold_bars_list = [int(t["hold_bars"]) for t in trades]

    wins = [r for r in realized_rs if r > 0]
    losses = [r for r in realized_rs if r <= 0]
    win_count = len(wins)
    loss_count = len(losses)

    win_rate = win_count / trade_count
    expectancy_r = _safe_mean(realized_rs)
    avg_r = expectancy_r
    median_r = _safe_median(realized_rs)

    # Equity curve for drawdown
    equity = []
    cumulative = 0.0
    for r in realized_rs:
        cumulative += r
        equity.append(cumulative)
    max_drawdown_r = compute_max_drawdown_r(equity)

    # Profit factor from R-multiples
    gross_wins = sum(wins)
    gross_losses = sum(losses)
    profit_factor = compute_profit_factor(gross_wins, gross_losses)

    avg_mfe_r = _safe_mean(mfes)
    avg_mae_r = _safe_mean(maes)
    exposure_bars = sum(hold_bars_list)
    avg_hold_bars = _safe_mean(hold_bars_list)

    # Quality adjusted score: expectancy * sqrt(trade_count) * win_rate
    quality_adjusted_score = expectancy_r * math.sqrt(trade_count) * win_rate

    # Sample adequacy: 1.0 at 30+ trades, scaling down
    sample_adequacy_score = min(1.0, trade_count / 30.0)

    return {
        "trade_count": trade_count,
        "win_rate": round(win_rate, 6),
        "expectancy_r": round(expectancy_r, 6),
        "avg_r": round(avg_r, 6),
        "median_r": round(median_r, 6),
        "max_drawdown_r": round(max_drawdown_r, 6),
        "profit_factor": round(profit_factor, 6),
        "avg_mfe_r": round(avg_mfe_r, 6),
        "avg_mae_r": round(avg_mae_r, 6),
        "exposure_bars": exposure_bars,
        "avg_hold_bars": round(avg_hold_bars, 6),
        "quality_adjusted_score": round(quality_adjusted_score, 6),
        "sample_adequacy_score": round(sample_adequacy_score, 6),
    }


def _get_metric(r: Dict[str, Any], key: str, default: Any = 0.0) -> Any:
    """Get metric from top-level or nested 'metrics' dict."""
    if key in r:
        return r[key]
    metrics = r.get("metrics", {})
    return metrics.get(key, default)


def compute_aggregate_metrics(
    run_results: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate metrics across multiple run results.

    Each run_result should be a dict containing at least the metrics keys
    returned by compute_run_metrics, either at top level or nested under
    a 'metrics' key.

    Returns aggregated dict with same keys, plus:
        run_count, total_trades, median_expectancy_r, worst_drawdown_r
    """
    if not run_results:
        return {
            "run_count": 0,
            "total_trades": 0,
            "trade_count": 0,
            "win_rate": 0.0,
            "expectancy_r": 0.0,
            "avg_r": 0.0,
            "median_r": 0.0,
            "max_drawdown_r": 0.0,
            "profit_factor": 0.0,
            "avg_mfe_r": 0.0,
            "avg_mae_r": 0.0,
            "exposure_bars": 0,
            "avg_hold_bars": 0.0,
            "quality_adjusted_score": 0.0,
            "sample_adequacy_score": 0.0,
            "median_expectancy_r": 0.0,
            "worst_drawdown_r": 0.0,
        }

    run_count = len(run_results)
    total_trades = sum(int(_get_metric(r, "trade_count", 0)) for r in run_results)

    # Weighted averages by trade_count where applicable
    expectancy_values = [float(_get_metric(r, "expectancy_r")) for r in run_results]
    drawdown_values = [float(_get_metric(r, "max_drawdown_r")) for r in run_results]
    win_rates = [float(_get_metric(r, "win_rate")) for r in run_results]
    profit_factors = [float(_get_metric(r, "profit_factor")) for r in run_results]
    quality_scores = [float(_get_metric(r, "quality_adjusted_score")) for r in run_results]
    sample_scores = [float(_get_metric(r, "sample_adequacy_score")) for r in run_results]
    avg_mfes = [float(_get_metric(r, "avg_mfe_r")) for r in run_results]
    avg_maes = [float(_get_metric(r, "avg_mae_r")) for r in run_results]
    exposure = [int(_get_metric(r, "exposure_bars", 0)) for r in run_results]
    hold_bars = [float(_get_metric(r, "avg_hold_bars")) for r in run_results]

    return {
        "run_count": run_count,
        "total_trades": total_trades,
        "trade_count": total_trades,
        "win_rate": round(_safe_mean(win_rates), 6),
        "expectancy_r": round(_safe_mean(expectancy_values), 6),
        "avg_r": round(_safe_mean(expectancy_values), 6),
        "median_r": round(_safe_median(expectancy_values), 6),
        "max_drawdown_r": round(min(drawdown_values) if drawdown_values else 0.0, 6),
        "profit_factor": round(_safe_mean(profit_factors), 6),
        "avg_mfe_r": round(_safe_mean(avg_mfes), 6),
        "avg_mae_r": round(_safe_mean(avg_maes), 6),
        "exposure_bars": sum(exposure),
        "avg_hold_bars": round(_safe_mean(hold_bars), 6),
        "quality_adjusted_score": round(_safe_mean(quality_scores), 6),
        "sample_adequacy_score": round(_safe_mean(sample_scores), 6),
        "median_expectancy_r": round(_safe_median(expectancy_values), 6),
        "worst_drawdown_r": round(min(drawdown_values) if drawdown_values else 0.0, 6),
    }
