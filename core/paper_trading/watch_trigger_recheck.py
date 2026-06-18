"""Watch trigger recheck — evaluates current SignalResult against previous watch plan. No orders, no network."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.paper_trading.readonly_signal_analyzer import SignalResult
from core.paper_trading.watch_trigger_planner import WatchTriggerPlan, plan_trigger


@dataclass(frozen=True)
class TriggerRecheckResult:
    symbol: str
    timeframe: str
    previous_action_label: str
    current_watch_state: str
    current_setup_type: str
    last_close: float
    recheck_status: str   # TRIGGERED / WAITING / INVALIDATED / SHORT_TRIGGERED / SHORT_WAITING / SHORT_INVALIDATED / DATA_ERROR
    trigger_reason: str
    invalidation_reason: str
    next_action: str      # OBSERVE_NOW / KEEP_WAITING / DROP_FROM_WATCH / SHORT_OBSERVE / DATA_SKIP
    risk_note: str


def recheck_trigger(current: SignalResult, previous_plan: Optional[WatchTriggerPlan] = None) -> TriggerRecheckResult:
    """Recheck a signal against its previous watch plan."""
    if previous_plan is None:
        previous_plan = plan_trigger(current)

    prev_action = previous_plan.action_label
    ws = current.watch_state

    # DATA_REJECT
    if ws == "DATA_REJECT":
        return TriggerRecheckResult(
            symbol=current.symbol, timeframe=current.timeframe,
            previous_action_label=prev_action,
            current_watch_state=ws, current_setup_type=current.setup_type,
            last_close=current.last_close,
            recheck_status="DATA_ERROR",
            trigger_reason="", invalidation_reason="data quality issue",
            next_action="DATA_SKIP",
            risk_note="data rejected",
        )

    # Previous was WAIT_CONFIRMATION (LONG_WATCH / NEAR_TURN_UP)
    if prev_action == "WAIT_CONFIRMATION":
        return _recheck_wait_confirmation(current, previous_plan)

    # Previous was SHORT_OBSERVE
    if prev_action == "SHORT_OBSERVE":
        return _recheck_short_observe(current, previous_plan)

    # Previous was WATCH_NOW (LONG_READY)
    if prev_action == "WATCH_NOW":
        return _recheck_watch_now(current, previous_plan)

    # Previous was AVOID or DATA_SKIP — just report current state
    if prev_action in ("AVOID", "DATA_SKIP"):
        return TriggerRecheckResult(
            symbol=current.symbol, timeframe=current.timeframe,
            previous_action_label=prev_action,
            current_watch_state=ws, current_setup_type=current.setup_type,
            last_close=current.last_close,
            recheck_status="WAITING" if ws not in ("DATA_REJECT",) else "DATA_ERROR",
            trigger_reason="", invalidation_reason="",
            next_action="KEEP_WAITING" if ws not in ("DATA_REJECT",) else "DATA_SKIP",
            risk_note=f"was AVOID, now {ws}",
        )

    # Fallback
    return TriggerRecheckResult(
        symbol=current.symbol, timeframe=current.timeframe,
        previous_action_label=prev_action,
        current_watch_state=ws, current_setup_type=current.setup_type,
        last_close=current.last_close,
        recheck_status="WAITING",
        trigger_reason="", invalidation_reason="",
        next_action="KEEP_WAITING",
        risk_note="unknown previous action",
    )


def _recheck_wait_confirmation(current: SignalResult, plan: WatchTriggerPlan) -> TriggerRecheckResult:
    ws = current.watch_state

    # TRIGGERED: watch_state improved to LONG_READY or MACD turned bullish
    if ws == "LONG_READY":
        return TriggerRecheckResult(
            symbol=current.symbol, timeframe=current.timeframe,
            previous_action_label=plan.action_label,
            current_watch_state=ws, current_setup_type=current.setup_type,
            last_close=current.last_close,
            recheck_status="TRIGGERED",
            trigger_reason=f"watch_state={ws}, MACD={current.macd_state}, trend={current.trend_bias}",
            invalidation_reason="",
            next_action="OBSERVE_NOW",
            risk_note=f"turning_score={current.turning_score}, dist_to_inv={current.distance_to_invalidation_pct}%",
        )

    if ws == "LONG_WATCH" and current.macd_state in ("BULLISH_CROSS", "HIST_EXPANDING_GREEN"):
        return TriggerRecheckResult(
            symbol=current.symbol, timeframe=current.timeframe,
            previous_action_label=plan.action_label,
            current_watch_state=ws, current_setup_type=current.setup_type,
            last_close=current.last_close,
            recheck_status="TRIGGERED",
            trigger_reason=f"MACD turned {current.macd_state} while LONG_WATCH",
            invalidation_reason="",
            next_action="OBSERVE_NOW",
            risk_note=f"turning_score={current.turning_score}",
        )

    # WAITING: still in NEAR_TURN_UP or LONG_WATCH
    if ws in ("NEAR_TURN_UP", "LONG_WATCH"):
        return TriggerRecheckResult(
            symbol=current.symbol, timeframe=current.timeframe,
            previous_action_label=plan.action_label,
            current_watch_state=ws, current_setup_type=current.setup_type,
            last_close=current.last_close,
            recheck_status="WAITING",
            trigger_reason=f"still {ws}, MACD={current.macd_state}",
            invalidation_reason="",
            next_action="KEEP_WAITING",
            risk_note=f"turning_score={current.turning_score}, waiting for MACD confirmation",
        )

    # INVALIDATED: degraded to WEAK_AVOID / SHORT_WATCH / CHOPPY_AVOID
    return TriggerRecheckResult(
        symbol=current.symbol, timeframe=current.timeframe,
        previous_action_label=plan.action_label,
        current_watch_state=ws, current_setup_type=current.setup_type,
        last_close=current.last_close,
        recheck_status="INVALIDATED",
        trigger_reason="",
        invalidation_reason=f"degraded from WAIT_CONFIRMATION to {ws}, MACD={current.macd_state}",
        next_action="DROP_FROM_WATCH",
        risk_note=f"weakness_score={current.weakness_score}",
    )


def _recheck_short_observe(current: SignalResult, plan: WatchTriggerPlan) -> TriggerRecheckResult:
    ws = current.watch_state

    # SHORT_TRIGGERED: still bearish, weakness confirmed
    if ws in ("SHORT_WATCH", "WEAK_AVOID") and current.weakness_score >= 40:
        return TriggerRecheckResult(
            symbol=current.symbol, timeframe=current.timeframe,
            previous_action_label=plan.action_label,
            current_watch_state=ws, current_setup_type=current.setup_type,
            last_close=current.last_close,
            recheck_status="SHORT_TRIGGERED",
            trigger_reason=f"weakness confirmed: {ws}, weakness_score={current.weakness_score}",
            invalidation_reason="",
            next_action="SHORT_OBSERVE",
            risk_note=f"bearish continuation, dist_to_inv={current.distance_to_invalidation_pct}%",
        )

    # SHORT_WAITING: still bearish but weakness not strong
    if ws in ("SHORT_WATCH", "WEAK_AVOID", "CHOPPY_AVOID"):
        return TriggerRecheckResult(
            symbol=current.symbol, timeframe=current.timeframe,
            previous_action_label=plan.action_label,
            current_watch_state=ws, current_setup_type=current.setup_type,
            last_close=current.last_close,
            recheck_status="SHORT_WAITING",
            trigger_reason=f"still {ws}",
            invalidation_reason="",
            next_action="SHORT_OBSERVE",
            risk_note=f"weakness_score={current.weakness_score}",
        )

    # SHORT_INVALIDATED: improved to LONG_WATCH / NEAR_TURN_UP / LONG_READY
    return TriggerRecheckResult(
        symbol=current.symbol, timeframe=current.timeframe,
        previous_action_label=plan.action_label,
        current_watch_state=ws, current_setup_type=current.setup_type,
        last_close=current.last_close,
        recheck_status="SHORT_INVALIDATED",
        trigger_reason="",
        invalidation_reason=f"improved from SHORT_OBSERVE to {ws}",
        next_action="DROP_FROM_WATCH",
        risk_note=f"bearish setup invalidated, turning_score={current.turning_score}",
    )


def _recheck_watch_now(current: SignalResult, plan: WatchTriggerPlan) -> TriggerRecheckResult:
    ws = current.watch_state

    if ws == "LONG_READY":
        return TriggerRecheckResult(
            symbol=current.symbol, timeframe=current.timeframe,
            previous_action_label=plan.action_label,
            current_watch_state=ws, current_setup_type=current.setup_type,
            last_close=current.last_close,
            recheck_status="TRIGGERED",
            trigger_reason=f"still LONG_READY, MACD={current.macd_state}",
            invalidation_reason="",
            next_action="OBSERVE_NOW",
            risk_note=f"maintained, dist_to_inv={current.distance_to_invalidation_pct}%",
        )

    if ws in ("LONG_WATCH", "NEAR_TURN_UP"):
        return TriggerRecheckResult(
            symbol=current.symbol, timeframe=current.timeframe,
            previous_action_label=plan.action_label,
            current_watch_state=ws, current_setup_type=current.setup_type,
            last_close=current.last_close,
            recheck_status="WAITING",
            trigger_reason=f"weakened to {ws} but still bullish area",
            invalidation_reason="",
            next_action="KEEP_WAITING",
            risk_note=f"turning_score={current.turning_score}",
        )

    return TriggerRecheckResult(
        symbol=current.symbol, timeframe=current.timeframe,
        previous_action_label=plan.action_label,
        current_watch_state=ws, current_setup_type=current.setup_type,
        last_close=current.last_close,
        recheck_status="INVALIDATED",
        trigger_reason="",
        invalidation_reason=f"degraded from LONG_READY to {ws}",
        next_action="DROP_FROM_WATCH",
        risk_note=f"weakness_score={current.weakness_score}",
    )
