"""Strategy registry — defines strategy types and their signal analysis logic.

Each strategy type processes MarketBar data and produces SignalCandidate results.
No orders, no secrets, no network (except via data_api adapter).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.paper_trading.readonly_signal_analyzer import SignalResult, analyze_bars
from core.paper_trading.data_source import MarketBar


@dataclass(frozen=True)
class SignalCandidate:
    """Unified signal output from any strategy."""
    strategy_id: str
    strategy_type: str
    symbol: str
    timeframe: str
    watch_state: str
    setup_type: str
    direction: str           # LONG_OBSERVE / SHORT_OBSERVE / NO_TRADE
    priority: str            # HIGH / MEDIUM / LOW
    last_close: float
    entry_observation: float
    invalidation_level: float
    take_profit_observation: float
    rr_ratio: float
    risk_distance_pct: float
    reward_distance_pct: float
    turning_score: int
    weakness_score: int
    risk_score: int
    macd_state: str
    rsi_state: str
    trend_bias: str
    volume_state: str
    reasons: list[str]
    risk_notes: str


@dataclass(frozen=True)
class StrategyRunResult:
    """Result of running one strategy on one symbol/timeframe."""
    strategy_id: str
    strategy_type: str
    symbol: str
    timeframe: str
    success: bool
    candidate: Optional[SignalCandidate]
    error: Optional[str]


def analyze_for_strategy(
    strategy_id: str,
    strategy_type: str,
    bars: list[MarketBar],
) -> StrategyRunResult:
    """Run signal analysis and filter based on strategy type."""
    if not bars:
        return StrategyRunResult(
            strategy_id=strategy_id, strategy_type=strategy_type,
            symbol="", timeframe="", success=False,
            candidate=None, error="empty bars",
        )

    sig = analyze_bars(bars)
    if sig is None:
        return StrategyRunResult(
            strategy_id=strategy_id, strategy_type=strategy_type,
            symbol=bars[0].symbol if bars else "", timeframe=bars[0].timeframe if bars else "",
            success=False, candidate=None, error="analysis failed",
        )

    candidate = _strategy_filter(strategy_id, strategy_type, sig)

    return StrategyRunResult(
        strategy_id=strategy_id, strategy_type=strategy_type,
        symbol=sig.symbol, timeframe=sig.timeframe,
        success=True, candidate=candidate, error=None,
    )


def _strategy_filter(
    strategy_id: str,
    strategy_type: str,
    sig: SignalResult,
) -> Optional[SignalCandidate]:
    """Filter signal based on strategy type. Returns None if signal doesn't match strategy."""
    ws = sig.watch_state

    if strategy_type == "macd_rebound_watch":
        return _filter_macd_rebound(strategy_id, strategy_type, sig)
    elif strategy_type == "weak_short_watch":
        return _filter_weak_short(strategy_id, strategy_type, sig)
    elif strategy_type == "breakout_pullback_watch":
        # Placeholder — not implemented yet
        return None
    else:
        return None


def _filter_macd_rebound(strategy_id: str, strategy_type: str, sig: SignalResult) -> Optional[SignalCandidate]:
    """MACD rebound watch: focus on LONG_READY, LONG_WATCH, NEAR_TURN_UP."""
    ws = sig.watch_state
    if ws not in ("LONG_READY", "LONG_WATCH", "NEAR_TURN_UP"):
        return None

    # Calculate TP as 2x risk
    entry = sig.entry_observation if sig.entry_observation > 0 else sig.last_close
    invalidation = sig.invalidation_level if sig.invalidation_level > 0 else entry * 0.98
    risk = abs(entry - invalidation)
    tp = entry + risk * 2.0 if entry > invalidation else 0.0
    rr = 2.0 if risk > 0 and tp > 0 else 0.0
    risk_dist = risk / entry * 100 if entry > 0 else 0.0
    reward_dist = abs(tp - entry) / entry * 100 if entry > 0 and tp > 0 else 0.0

    priority = "HIGH" if ws == "LONG_READY" else "MEDIUM" if ws == "LONG_WATCH" else "LOW"

    return SignalCandidate(
        strategy_id=strategy_id, strategy_type=strategy_type,
        symbol=sig.symbol, timeframe=sig.timeframe,
        watch_state=ws, setup_type=sig.setup_type,
        direction="LONG_OBSERVE", priority=priority,
        last_close=sig.last_close,
        entry_observation=round(entry, 6),
        invalidation_level=round(invalidation, 6),
        take_profit_observation=round(tp, 6),
        rr_ratio=round(rr, 2),
        risk_distance_pct=round(risk_dist, 2),
        reward_distance_pct=round(reward_dist, 2),
        turning_score=sig.turning_score, weakness_score=sig.weakness_score,
        risk_score=sig.risk_score, macd_state=sig.macd_state,
        rsi_state=sig.rsi_state, trend_bias=sig.trend_bias,
        volume_state=sig.volume_state, reasons=sig.reasons,
        risk_notes=sig.risk_notes,
    )


def _filter_weak_short(strategy_id: str, strategy_type: str, sig: SignalResult) -> Optional[SignalCandidate]:
    """Weak short watch: focus on SHORT_WATCH, WEAK_AVOID."""
    ws = sig.watch_state
    if ws not in ("SHORT_WATCH", "WEAK_AVOID"):
        return None

    # Calculate TP as 2x risk below entry
    entry = sig.entry_observation if sig.entry_observation > 0 else sig.last_close
    invalidation = sig.invalidation_level if sig.invalidation_level > 0 else entry * 1.02
    risk = abs(invalidation - entry)
    tp = entry - risk * 2.0 if invalidation > entry else 0.0
    rr = 2.0 if risk > 0 and tp > 0 else 0.0
    risk_dist = risk / entry * 100 if entry > 0 else 0.0
    reward_dist = abs(tp - entry) / entry * 100 if entry > 0 and tp > 0 else 0.0

    priority = "HIGH" if ws == "SHORT_WATCH" and sig.weakness_score >= 60 else "MEDIUM"

    return SignalCandidate(
        strategy_id=strategy_id, strategy_type=strategy_type,
        symbol=sig.symbol, timeframe=sig.timeframe,
        watch_state=ws, setup_type=sig.setup_type,
        direction="SHORT_OBSERVE", priority=priority,
        last_close=sig.last_close,
        entry_observation=round(entry, 6),
        invalidation_level=round(invalidation, 6),
        take_profit_observation=round(tp, 6),
        rr_ratio=round(rr, 2),
        risk_distance_pct=round(risk_dist, 2),
        reward_distance_pct=round(reward_dist, 2),
        turning_score=sig.turning_score, weakness_score=sig.weakness_score,
        risk_score=sig.risk_score, macd_state=sig.macd_state,
        rsi_state=sig.rsi_state, trend_bias=sig.trend_bias,
        volume_state=sig.volume_state, reasons=sig.reasons,
        risk_notes=sig.risk_notes,
    )
