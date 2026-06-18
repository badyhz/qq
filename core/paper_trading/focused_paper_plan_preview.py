"""Focused paper plan preview — generates paper-only trade plan previews from signal + recheck. No orders, no network."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.paper_trading.readonly_signal_analyzer import SignalResult
from core.paper_trading.watch_trigger_recheck import TriggerRecheckResult


SAFETY_FLAGS = [
    "PAPER_ONLY", "PUBLIC_READONLY_ONLY", "NO_SECRET", "NO_ACCOUNT",
    "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT",
]


@dataclass(frozen=True)
class FocusedPaperPlan:
    symbol: str
    timeframe: str
    direction: str            # LONG_OBSERVE / SHORT_OBSERVE / NO_TRADE
    source_status: str        # TRIGGERED / WAITING / SHORT_TRIGGERED / etc.
    last_close: float
    entry_observation: float
    invalidation_level: float
    take_profit_observation: float
    rr_ratio: float
    risk_distance_pct: float
    reward_distance_pct: float
    plan_decision: str        # WATCH / WAIT / AVOID
    reason: str
    safety_flags: list[str]


def preview_plan(
    sig: SignalResult,
    recheck: TriggerRecheckResult,
) -> FocusedPaperPlan:
    """Generate a focused paper plan preview from a signal and its recheck result."""
    status = recheck.recheck_status
    ws = sig.watch_state
    close = sig.last_close

    # Entry observation from signal
    entry = sig.entry_observation if sig.entry_observation > 0 else close
    invalidation = sig.invalidation_level if sig.invalidation_level > 0 else _default_invalidation(sig)

    # Determine direction and TP based on recheck status
    if status == "TRIGGERED":
        direction = "LONG_OBSERVE"
        tp = _estimate_long_tp(entry, invalidation, sig)
        decision = "WATCH" if _calc_rr(entry, invalidation, tp) >= 1.5 else "WAIT"
        reason = f"long triggered: {recheck.trigger_reason}"

    elif status == "WAITING":
        direction = "LONG_OBSERVE"
        tp = _estimate_long_tp(entry, invalidation, sig)
        decision = "WAIT"
        reason = f"still waiting: {recheck.trigger_reason}"

    elif status == "SHORT_TRIGGERED":
        direction = "SHORT_OBSERVE"
        tp = _estimate_short_tp(entry, invalidation, sig)
        decision = "WATCH" if _calc_rr(entry, invalidation, tp) >= 1.5 else "WAIT"
        reason = f"short triggered: {recheck.trigger_reason}"

    elif status == "SHORT_WAITING":
        direction = "SHORT_OBSERVE"
        tp = _estimate_short_tp(entry, invalidation, sig)
        decision = "WAIT"
        reason = f"short waiting: {recheck.trigger_reason}"

    else:
        # INVALIDATED / SHORT_INVALIDATED / DATA_ERROR
        direction = "NO_TRADE"
        tp = 0.0
        decision = "AVOID"
        reason = recheck.invalidation_reason or f"status={status}"

    rr = _calc_rr(entry, invalidation, tp) if tp > 0 and entry > 0 and invalidation > 0 else 0.0
    risk_dist = abs(entry - invalidation) / entry * 100 if entry > 0 and invalidation > 0 else 0.0
    reward_dist = abs(tp - entry) / entry * 100 if entry > 0 and tp > 0 else 0.0

    return FocusedPaperPlan(
        symbol=sig.symbol,
        timeframe=sig.timeframe,
        direction=direction,
        source_status=status,
        last_close=close,
        entry_observation=round(entry, 6),
        invalidation_level=round(invalidation, 6),
        take_profit_observation=round(tp, 6),
        rr_ratio=round(rr, 2),
        risk_distance_pct=round(risk_dist, 2),
        reward_distance_pct=round(reward_dist, 2),
        plan_decision=decision,
        reason=reason,
        safety_flags=list(SAFETY_FLAGS),
    )


def _default_invalidation(sig: SignalResult) -> float:
    """Fallback invalidation if signal doesn't provide one."""
    close = sig.last_close
    if close <= 0:
        return 0.0
    # Use 2% below close for longs, 2% above for shorts
    if sig.watch_state in ("SHORT_WATCH", "WEAK_AVOID"):
        return close * 1.02
    return close * 0.98


def _estimate_long_tp(entry: float, invalidation: float, sig: SignalResult) -> float:
    """Estimate long take-profit as 2x risk distance from entry."""
    if entry <= 0 or invalidation <= 0 or entry <= invalidation:
        return 0.0
    risk = entry - invalidation
    return entry + risk * 2.0


def _estimate_short_tp(entry: float, invalidation: float, sig: SignalResult) -> float:
    """Estimate short take-profit as 2x risk distance from entry."""
    if entry <= 0 or invalidation <= 0 or entry >= invalidation:
        return 0.0
    risk = invalidation - entry
    return entry - risk * 2.0


def _calc_rr(entry: float, invalidation: float, tp: float) -> float:
    """Calculate risk/reward ratio. Returns 0 if inputs invalid."""
    if entry <= 0 or invalidation <= 0 or tp <= 0:
        return 0.0
    risk = abs(entry - invalidation)
    reward = abs(tp - entry)
    if risk <= 0:
        return 0.0
    return reward / risk
