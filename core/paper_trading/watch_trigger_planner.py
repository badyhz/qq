"""Watch trigger planner — generates actionable watch plans from SignalResult. No orders, no network."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from core.paper_trading.readonly_signal_analyzer import SignalResult


@dataclass(frozen=True)
class WatchTriggerPlan:
    symbol: str
    timeframe: str
    watch_state: str
    setup_type: str
    priority: str
    last_close: float
    trigger_type: str           # MACD_TURN_CONFIRM / BREAKOUT_CONFIRM / PULLBACK_HOLD / WEAKNESS_CONTINUATION / AVOID / DATA_REJECT
    trigger_condition: str
    confirmation_condition: str
    invalidation_condition: str
    risk_note: str
    wait_note: str
    action_label: str           # WATCH_NOW / WAIT_CONFIRMATION / AVOID / SHORT_OBSERVE / DATA_SKIP
    shadow_record_type: str     # WATCH_TRIGGER / OBSERVATION / SKIP


def plan_trigger(sig: SignalResult) -> WatchTriggerPlan:
    """Generate a WatchTriggerPlan from a SignalResult."""
    ws = sig.watch_state

    if ws == "DATA_REJECT":
        return WatchTriggerPlan(
            symbol=sig.symbol, timeframe=sig.timeframe,
            watch_state=ws, setup_type=sig.setup_type,
            priority=sig.priority, last_close=sig.last_close,
            trigger_type="DATA_REJECT",
            trigger_condition="none — data quality issue",
            confirmation_condition="",
            invalidation_condition="wait for valid data",
            risk_note="data rejected, do not act",
            wait_note="re-check after data improves",
            action_label="DATA_SKIP",
            shadow_record_type="SKIP",
        )

    if ws == "CHOPPY_AVOID":
        return WatchTriggerPlan(
            symbol=sig.symbol, timeframe=sig.timeframe,
            watch_state=ws, setup_type=sig.setup_type,
            priority=sig.priority, last_close=sig.last_close,
            trigger_type="AVOID",
            trigger_condition="none — no clear direction",
            confirmation_condition="",
            invalidation_condition="wait until trend exits chop (EMA spread > 0.5%, MACD picks direction)",
            risk_note="choppy market, whipsaw risk",
            wait_note="monitor for trend emergence",
            action_label="AVOID",
            shadow_record_type="SKIP",
        )

    if ws == "WEAK_AVOID":
        return WatchTriggerPlan(
            symbol=sig.symbol, timeframe=sig.timeframe,
            watch_state=ws, setup_type=sig.setup_type,
            priority=sig.priority, last_close=sig.last_close,
            trigger_type="AVOID",
            trigger_condition="none — bearish/weak, no long setup",
            confirmation_condition="",
            invalidation_condition="wait until watch_state improves to NEAR_TURN_UP or LONG_WATCH",
            risk_note=f"weakness_score={sig.weakness_score}, avoid longs",
            wait_note="monitor for MACD histogram shrink + RSI recovery",
            action_label="AVOID",
            shadow_record_type="SKIP",
        )

    if ws == "SHORT_WATCH":
        inv = sig.invalidation_level
        return WatchTriggerPlan(
            symbol=sig.symbol, timeframe=sig.timeframe,
            watch_state=ws, setup_type=sig.setup_type,
            priority=sig.priority, last_close=sig.last_close,
            trigger_type="WEAKNESS_CONTINUATION",
            trigger_condition=f"price continues below {inv:.2f} + MACD stays red expanding",
            confirmation_condition="RSI stays below 50 + volume normal or spike",
            invalidation_condition=f"price reclaims EMA cluster or MACD turns green (above {inv:.2f})",
            risk_note=f"dist_to_inv={sig.distance_to_invalidation_pct}%, risk_score={sig.risk_score}",
            wait_note="bearish continuation watch — do not long",
            action_label="SHORT_OBSERVE",
            shadow_record_type="OBSERVATION",
        )

    if ws == "NEAR_TURN_UP":
        inv = sig.invalidation_level
        return WatchTriggerPlan(
            symbol=sig.symbol, timeframe=sig.timeframe,
            watch_state=ws, setup_type=sig.setup_type,
            priority=sig.priority, last_close=sig.last_close,
            trigger_type="MACD_TURN_CONFIRM",
            trigger_condition=f"MACD histogram turns green or bullish cross + price holds above {inv:.2f}",
            confirmation_condition=f"RSI not overbought (< 70) + price holds above recent low ({sig.distance_to_recent_low_pct}% above low)",
            invalidation_condition=f"breaks recent low or invalidation_level ({inv:.2f})",
            risk_note=f"turning_score={sig.turning_score}, dist_to_inv={sig.distance_to_invalidation_pct}%",
            wait_note="wait for MACD confirmation before watching as LONG",
            action_label="WAIT_CONFIRMATION",
            shadow_record_type="WATCH_TRIGGER",
        )

    if ws == "LONG_WATCH":
        inv = sig.invalidation_level
        return WatchTriggerPlan(
            symbol=sig.symbol, timeframe=sig.timeframe,
            watch_state=ws, setup_type=sig.setup_type,
            priority=sig.priority, last_close=sig.last_close,
            trigger_type="PULLBACK_HOLD",
            trigger_condition=f"MACD histogram keeps improving + price holds above {inv:.2f}",
            confirmation_condition="RSI stays neutral (30-70) + volume normal or spike",
            invalidation_condition=f"breaks invalidation_level ({inv:.2f}) or MACD turns red expanding",
            risk_note=f"turning_score={sig.turning_score}, dist_to_inv={sig.distance_to_invalidation_pct}%",
            wait_note="pullback setup forming — wait for strength confirmation",
            action_label="WAIT_CONFIRMATION",
            shadow_record_type="WATCH_TRIGGER",
        )

    if ws == "LONG_READY":
        inv = sig.invalidation_level
        high = sig.last_close * (1 + sig.distance_to_recent_high_pct / 100)
        return WatchTriggerPlan(
            symbol=sig.symbol, timeframe=sig.timeframe,
            watch_state=ws, setup_type=sig.setup_type,
            priority=sig.priority, last_close=sig.last_close,
            trigger_type="BREAKOUT_CONFIRM",
            trigger_condition=f"price holds above {sig.last_close:.2f} or breaks recent high ({high:.2f})",
            confirmation_condition=f"MACD stays green + RSI not overbought + volume supports",
            invalidation_condition=f"breaks invalidation_level ({inv:.2f})",
            risk_note=f"dist_to_inv={sig.distance_to_invalidation_pct}%, risk_score={sig.risk_score}",
            wait_note="strong setup — watch for continuation",
            action_label="WATCH_NOW",
            shadow_record_type="WATCH_TRIGGER",
        )

    # Fallback
    return WatchTriggerPlan(
        symbol=sig.symbol, timeframe=sig.timeframe,
        watch_state=ws, setup_type=sig.setup_type,
        priority=sig.priority, last_close=sig.last_close,
        trigger_type="AVOID",
        trigger_condition="none",
        confirmation_condition="",
        invalidation_condition="",
        risk_note="unknown state",
        wait_note="no action",
        action_label="AVOID",
        shadow_record_type="SKIP",
    )
