"""Offline backtest trade simulator — pure functions, no I/O.

Simulates trade outcomes from signal entries against bar data.
Computes P&L, R-multiples, MFE/MAE, hold duration, slippage, and fees.

Legacy signals keep the original behavior: their entry bar is treated as the
observation bar and price-path simulation begins on the following bar.
Signals that explicitly set ``entry_execution='bar_open'`` are filled at that
bar's open and are exposed to that same bar's high/low path. This enables a
closed-signal -> next-bar-open execution contract without creating a second
simulator or changing existing callers.
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

    Required signal keys: ``signal_id``, ``entry_bar_index``, ``entry_price``,
    ``stop_price`` and ``tp_price``.

    Optional ``entry_execution`` values:
    - ``observation_price`` (default): preserve legacy behavior and begin path
      simulation on the bar after ``entry_bar_index``;
    - ``bar_open``: ``entry_price`` is the selected entry bar's open, so stop/
      target checks begin on that same bar.
    """
    if params is None:
        params = TradeSimulationParams()

    signal_id = signal.get("signal_id", "unknown")
    entry_idx = int(signal["entry_bar_index"])
    entry_price = float(signal["entry_price"])
    stop_price = float(signal["stop_price"])
    tp_price = float(signal["tp_price"])
    entry_execution = str(signal.get("entry_execution") or "observation_price")
    if entry_execution not in {"observation_price", "bar_open"}:
        raise ValueError(f"unsupported entry_execution: {entry_execution}")
    if entry_idx < 0 or entry_idx >= len(bars):
        raise ValueError("entry_bar_index is outside bar data")

    # Direction: SHORT if stop > entry, LONG if stop < entry
    is_short = stop_price > entry_price

    # Apply adverse slippage to entry.
    if is_short:
        actual_entry = entry_price * (1 - params.slippage_pct)
    else:
        actual_entry = entry_price * (1 + params.slippage_pct)

    risk_distance = abs(actual_entry - stop_price)
    if risk_distance <= 0:
        risk_distance = entry_price * 0.01  # legacy fallback 1%

    best_favorable = 0.0
    worst_adverse = 0.0

    exit_idx = entry_idx
    exit_price = actual_entry
    exit_reason = ExitReason.END_OF_DATA.value
    scan_start = entry_idx if entry_execution == "bar_open" else entry_idx + 1

    for i in range(scan_start, min(entry_idx + params.max_hold_bars + 1, len(bars))):
        bar = bars[i]
        high = float(bar["high"])
        low = float(bar["low"])

        if is_short:
            favorable = (actual_entry - low) / risk_distance
            adverse = (high - actual_entry) / risk_distance
        else:
            favorable = (high - actual_entry) / risk_distance
            adverse = (actual_entry - low) / risk_distance

        best_favorable = max(best_favorable, favorable)
        worst_adverse = max(worst_adverse, adverse)

        # Preserve existing conservative intrabar ambiguity rule: stop first.
        if is_short and high >= stop_price:
            exit_idx = i
            exit_price = stop_price * (1 + params.slippage_pct)
            exit_reason = ExitReason.STOP_LOSS.value
            break
        if not is_short and low <= stop_price:
            exit_idx = i
            exit_price = stop_price * (1 - params.slippage_pct)
            exit_reason = ExitReason.STOP_LOSS.value
            break

        if is_short and low <= tp_price:
            exit_idx = i
            exit_price = tp_price * (1 + params.slippage_pct)
            exit_reason = ExitReason.TAKE_PROFIT.value
            break
        if not is_short and high >= tp_price:
            exit_idx = i
            exit_price = tp_price * (1 - params.slippage_pct)
            exit_reason = ExitReason.TAKE_PROFIT.value
            break

        exit_idx = i

    if (
        exit_reason == ExitReason.END_OF_DATA.value
        and exit_idx >= entry_idx + params.max_hold_bars
    ):
        exit_reason = ExitReason.MAX_HOLD.value

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
