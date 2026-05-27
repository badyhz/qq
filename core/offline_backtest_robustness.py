"""Offline backtest robustness checks — pure functions.

Sensitivity analysis for fees, slippage, min trades, and split stability.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Sequence


@dataclass(frozen=True)
class RobustnessReport:
    """Immutable report from a robustness check."""
    check_name: str
    passes: tuple  # tuple[str, ...] — parameter values that passed
    fails: tuple   # tuple[str, ...] — parameter values that failed
    is_robust: bool
    detail: str

    def __post_init__(self) -> None:
        if not self.check_name:
            raise ValueError("check_name must be non-empty")
        if not isinstance(self.passes, tuple):
            raise ValueError("passes must be a tuple")
        if not isinstance(self.fails, tuple):
            raise ValueError("fails must be a tuple")


def _apply_fee_adjustment(
    trades: Sequence[Dict[str, Any]],
    fee_bps: float,
) -> Sequence[Dict[str, Any]]:
    """Return trades with adjusted net_pnl for a given fee in basis points."""
    adjusted = []
    for t in trades:
        entry_price = float(t.get("entry_price", 100.0))
        extra_fee = entry_price * (fee_bps / 10000.0)
        original_net = float(t.get("net_pnl", 0.0))
        adjusted.append({**t, "net_pnl": original_net - extra_fee})
    return adjusted


def _apply_slippage_adjustment(
    trades: Sequence[Dict[str, Any]],
    slippage_bps: float,
) -> Sequence[Dict[str, Any]]:
    """Return trades with adjusted entry/exit prices for slippage."""
    adjusted = []
    for t in trades:
        entry = float(t.get("entry_price", 100.0))
        slip = entry * (slippage_bps / 10000.0)
        original_net = float(t.get("net_pnl", 0.0))
        adjusted.append({**t, "net_pnl": original_net - slip})
    return adjusted


def check_fee_sensitivity(
    run_results: Sequence[Dict[str, Any]],
    fee_range_bps: Sequence[float],
) -> RobustnessReport:
    """Check if strategy remains profitable across fee levels.

    run_results: list of dicts with at least 'trades' (list of trade dicts)
        and 'profitable' threshold (default: expectancy_r > 0).
    fee_range_bps: list of fee values in basis points to test.

    Returns RobustnessReport.
    """
    passes: list[str] = []
    fails: list[str] = []

    for fee_bps in fee_range_bps:
        all_positive = True
        for run in run_results:
            trades = run.get("trades", [])
            if not trades:
                continue
            adjusted = _apply_fee_adjustment(trades, fee_bps)
            net_pnls = [float(t.get("net_pnl", 0.0)) for t in adjusted]
            avg = sum(net_pnls) / len(net_pnls) if net_pnls else 0.0
            if avg <= 0:
                all_positive = False
                break
        label = f"{fee_bps}bps"
        if all_positive:
            passes.append(label)
        else:
            fails.append(label)

    return RobustnessReport(
        check_name="fee_sensitivity",
        passes=tuple(passes),
        fails=tuple(fails),
        is_robust=len(fails) == 0,
        detail=f"{len(passes)}/{len(fee_range_bps)} fee levels profitable",
    )


def check_slippage_sensitivity(
    run_results: Sequence[Dict[str, Any]],
    slippage_range_bps: Sequence[float],
) -> RobustnessReport:
    """Check if strategy remains profitable across slippage levels."""
    passes: list[str] = []
    fails: list[str] = []

    for slip_bps in slippage_range_bps:
        all_positive = True
        for run in run_results:
            trades = run.get("trades", [])
            if not trades:
                continue
            adjusted = _apply_slippage_adjustment(trades, slip_bps)
            net_pnls = [float(t.get("net_pnl", 0.0)) for t in adjusted]
            avg = sum(net_pnls) / len(net_pnls) if net_pnls else 0.0
            if avg <= 0:
                all_positive = False
                break
        label = f"{slip_bps}bps"
        if all_positive:
            passes.append(label)
        else:
            fails.append(label)

    return RobustnessReport(
        check_name="slippage_sensitivity",
        passes=tuple(passes),
        fails=tuple(fails),
        is_robust=len(fails) == 0,
        detail=f"{len(passes)}/{len(slippage_range_bps)} slippage levels profitable",
    )


def check_min_trade_threshold(
    run_results: Sequence[Dict[str, Any]],
    min_trades_range: Sequence[int],
) -> RobustnessReport:
    """Check if each run meets minimum trade count thresholds."""
    passes: list[str] = []
    fails: list[str] = []

    for min_t in min_trades_range:
        all_meet = True
        for run in run_results:
            trade_count = int(run.get("trade_count", 0))
            if trade_count < min_t:
                all_meet = False
                break
        label = str(min_t)
        if all_meet:
            passes.append(label)
        else:
            fails.append(label)

    return RobustnessReport(
        check_name="min_trade_threshold",
        passes=tuple(passes),
        fails=tuple(fails),
        is_robust=len(fails) == 0,
        detail=f"{len(passes)}/{len(min_trades_range)} thresholds met",
    )


def check_split_stability(
    run_results: Sequence[Dict[str, Any]],
) -> RobustnessReport:
    """Check if performance is stable across walk-forward splits.

    Expects run_results to have 'split_id' and 'expectancy_r' keys.
    Stable = all splits have positive expectancy.
    """
    passes: list[str] = []
    fails: list[str] = []

    for run in run_results:
        split_id = str(run.get("split_id", "unknown"))
        expectancy = float(run.get("expectancy_r", 0.0))
        if expectancy > 0:
            passes.append(split_id)
        else:
            fails.append(split_id)

    return RobustnessReport(
        check_name="split_stability",
        passes=tuple(passes),
        fails=tuple(fails),
        is_robust=len(fails) == 0,
        detail=f"{len(passes)}/{len(run_results)} splits positive",
    )
