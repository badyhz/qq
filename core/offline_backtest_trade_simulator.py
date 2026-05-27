"""Offline backtest trade simulator — pure functions, no I/O.

Simulates trade outcomes from signal entries against bar data.
Computes P&L, R-multiples, MFE/MAE, hold duration, slippage, and fees.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence


class ExitReason(str, Enum):
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    MAX_HOLD = "MAX_HOLD"
    END_OF_DATA = "END_OF_DATA"


@dataclass(frozen=True)
class TradeSimulationParams:
    """Parameters controlling trade simulation behavior."""
    slippage_pct: float = 0.0005
    fee_pct: float = 0.001
    max_hold_bars: int = 100
    risk_per_trade_r: float = 1.0

    def __post_init__(self) -> None:
        if self.slippage_pct < 0:
            raise ValueError("slippage_pct must be >= 0")
        if self.fee_pct < 0:
            raise ValueError("fee_pct must be >= 0")
        if self.max_hold_bars <= 0:
            raise ValueError("max_hold_bars must be > 0")


@dataclass(frozen=True)
class TradeOutcome:
    """Result of simulating a single trade."""
    trade_id: str
    signal_id: str
    entry_bar_index: int
    exit_bar_index: int
    entry_price: float
    exit_price: float
    exit_reason: str
    realized_r: float
    gross_pnl: float
    fees: float
    slippage_cost: float
    net_pnl: float
    mfe_r: float
    mae_r: float
    hold_bars: int


def simulate_trade(
    signal: dict,
    bars: Sequence[dict],
    params: TradeSimulationParams | None = None,
) -> TradeOutcome:
    """Simulate a single trade from a signal against bar data.

    Parameters
    ----------
    signal : dict
        Must have: signal_id, entry_bar_index, entry_price, stop_price, tp_price.
    bars : Sequence[dict]
        Bar dicts with open/high/low/close/volume.
    params : TradeSimulationParams, optional

    Returns
    -------
    TradeOutcome
    """
    if params is None:
        params = TradeSimulationParams()

    signal_id = signal.get("signal_id", "unknown")
    entry_idx = int(signal["entry_bar_index"])
    entry_price = float(signal["entry_price"])
    stop_price = float(signal["stop_price"])
    tp_price = float(signal["tp_price"])

    # Direction: SHORT if stop > entry, LONG if stop < entry
    is_short = stop_price > entry_price

    # Apply slippage to entry
    if is_short:
        actual_entry = entry_price * (1 - params.slippage_pct)
    else:
        actual_entry = entry_price * (1 + params.slippage_pct)

    # Risk distance in R
    risk_distance = abs(actual_entry - stop_price)
    if risk_distance <= 0:
        risk_distance = entry_price * 0.01  # fallback 1%

    best_favorable = 0.0
    worst_adverse = 0.0

    exit_idx = entry_idx
    exit_price = actual_entry
    exit_reason = ExitReason.END_OF_DATA.value

    for i in range(entry_idx + 1, min(entry_idx + params.max_hold_bars + 1, len(bars))):
        bar = bars[i]
        high = float(bar["high"])
        low = float(bar["low"])

        # Compute excursion in R
        if is_short:
            favorable = (actual_entry - low) / risk_distance
            adverse = (high - actual_entry) / risk_distance
        else:
            favorable = (high - actual_entry) / risk_distance
            adverse = (actual_entry - low) / risk_distance

        best_favorable = max(best_favorable, favorable)
        worst_adverse = max(worst_adverse, adverse)

        # Check stop loss
        if is_short and high >= stop_price:
            exit_idx = i
            exit_price = stop_price * (1 + params.slippage_pct)
            exit_reason = ExitReason.STOP_LOSS.value
            break
        elif not is_short and low <= stop_price:
            exit_idx = i
            exit_price = stop_price * (1 - params.slippage_pct)
            exit_reason = ExitReason.STOP_LOSS.value
            break

        # Check take profit
        if is_short and low <= tp_price:
            exit_idx = i
            exit_price = tp_price * (1 + params.slippage_pct)
            exit_reason = ExitReason.TAKE_PROFIT.value
            break
        elif not is_short and high >= tp_price:
            exit_idx = i
            exit_price = tp_price * (1 - params.slippage_pct)
            exit_reason = ExitReason.TAKE_PROFIT.value
            break

        exit_idx = i

    # If max hold exceeded
    if exit_reason == ExitReason.END_OF_DATA.value and exit_idx >= entry_idx + params.max_hold_bars:
        exit_reason = ExitReason.MAX_HOLD.value

    # P&L calculation
    if is_short:
        gross_pnl = actual_entry - exit_price
    else:
        gross_pnl = exit_price - actual_entry

    slippage_cost = abs(actual_entry - entry_price)
    fees = (actual_entry + exit_price) * params.fee_pct
    net_pnl = gross_pnl - fees - slippage_cost
    realized_r = net_pnl / risk_distance if risk_distance > 0 else 0.0

    return TradeOutcome(
        trade_id=f"trade_{signal_id}",
        signal_id=signal_id,
        entry_bar_index=entry_idx,
        exit_bar_index=exit_idx,
        entry_price=actual_entry,
        exit_price=exit_price,
        exit_reason=exit_reason,
        realized_r=round(realized_r, 6),
        gross_pnl=round(gross_pnl, 6),
        fees=round(fees, 6),
        slippage_cost=round(slippage_cost, 6),
        net_pnl=round(net_pnl, 6),
        mfe_r=round(best_favorable, 6),
        mae_r=round(worst_adverse, 6),
        hold_bars=exit_idx - entry_idx,
    )


def apply_slippage(price: float, slippage_bps: float, direction: str = "long") -> float:
    """Apply slippage to a price in basis points.

    For longs, slippage increases buy price (adverse).
    """
    if price <= 0:
        raise ValueError(f"price must be > 0, got {price}")
    if slippage_bps < 0:
        raise ValueError(f"slippage_bps must be >= 0, got {slippage_bps}")
    if direction == "long":
        return price * (1.0 + slippage_bps / 10000.0)
    else:
        return price * (1.0 - slippage_bps / 10000.0)


def apply_fee(notional: float, fee_bps: float) -> float:
    """Calculate fee from notional value in basis points."""
    if fee_bps < 0:
        raise ValueError(f"fee_bps must be >= 0, got {fee_bps}")
    return abs(notional) * fee_bps / 10000.0


def compute_r_metric(entry: float, exit_: float, stop_loss: float) -> float:
    """Compute realized R-metric: (exit - entry) / (entry - stop_loss).

    Returns 0 if risk distance is <= 0.
    """
    risk = entry - stop_loss
    if risk <= 0:
        return 0.0
    return (exit_ - entry) / risk
