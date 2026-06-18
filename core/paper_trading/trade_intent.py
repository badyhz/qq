"""Trade intent — shadow-only representation of a potential trade.

No orders, no accounts, no secrets, no testnet, no live.
execution_mode is always shadow_only.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


TRADE_INTENT_SAFETY_FLAGS = [
    "PAPER_ONLY",
    "SHADOW_ONLY",
    "NO_ORDER",
    "NO_REAL_ORDER",
    "NO_ACCOUNT",
    "NO_SECRET",
    "NO_TESTNET",
    "NO_LIVE",
    "NO_WEBSOCKET",
    "NO_WEBHOOK_SEND",
    "POSITION_SIZE_PREVIEW_ONLY",
]

SIDE_MAP = {
    "LONG_OBSERVE": "LONG",
    "SHORT_OBSERVE": "SHORT",
    "NO_TRADE": "NO_TRADE",
}

DEFAULT_PAPER_EQUITY = 10000.0
DEFAULT_MAX_RISK_PCT = 0.5


@dataclass(frozen=True)
class TradeIntent:
    """Shadow-only trade intent. Never results in a real order."""
    intent_id: str
    date: str
    source: str
    strategy_id: str
    strategy_type: str
    symbol: str
    timeframe: str
    side: str
    intent_status: str
    execution_mode: str
    entry_type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    rr_ratio: float
    risk_distance_pct: float
    reward_distance_pct: float
    max_risk_pct: float
    notional_mode: str
    position_size_preview: float
    position_size_reason: str
    source_priority: str
    source_watch_state: str
    source_reason: str
    risk_gate_status: str
    risk_gate_reasons: list[str]
    safety_flags: list[str]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "date": self.date,
            "source": self.source,
            "strategy_id": self.strategy_id,
            "strategy_type": self.strategy_type,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "side": self.side,
            "intent_status": self.intent_status,
            "execution_mode": self.execution_mode,
            "entry_type": self.entry_type,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "rr_ratio": self.rr_ratio,
            "risk_distance_pct": self.risk_distance_pct,
            "reward_distance_pct": self.reward_distance_pct,
            "max_risk_pct": self.max_risk_pct,
            "notional_mode": self.notional_mode,
            "position_size_preview": self.position_size_preview,
            "position_size_reason": self.position_size_reason,
            "source_priority": self.source_priority,
            "source_watch_state": self.source_watch_state,
            "source_reason": self.source_reason,
            "risk_gate_status": self.risk_gate_status,
            "risk_gate_reasons": list(self.risk_gate_reasons),
            "safety_flags": list(self.safety_flags),
            "created_at": self.created_at,
        }


def build_trade_intent(
    plan: dict[str, Any],
    date_str: str,
    paper_equity: float = DEFAULT_PAPER_EQUITY,
    max_risk_pct: float = DEFAULT_MAX_RISK_PCT,
) -> TradeIntent:
    """Build a TradeIntent from a strategy payload input plan."""
    direction = str(plan.get("direction") or "NO_TRADE")
    side = SIDE_MAP.get(direction, "NO_TRADE")

    entry_price = float(plan.get("entry_observation") or 0)
    stop_loss = float(plan.get("invalidation_level") or 0)
    take_profit = float(plan.get("take_profit_observation") or 0)
    rr_ratio = float(plan.get("rr_ratio") or 0)
    risk_dist = float(plan.get("risk_distance_pct") or 0)
    reward_dist = float(plan.get("reward_distance_pct") or 0)
    strategy_id = str(plan.get("reason", "").split(":")[0].strip() or "unknown")

    # Determine intent_status
    intent_status, risk_reasons = _determine_status(
        side, entry_price, stop_loss, take_profit, rr_ratio, risk_dist, reward_dist, max_risk_pct,
    )

    # Calculate position size preview
    pos_size, pos_reason = _calc_position_size(
        side, entry_price, stop_loss, paper_equity, max_risk_pct, intent_status,
    )

    return TradeIntent(
        intent_id=f"TI_{uuid.uuid4().hex[:12]}",
        date=date_str,
        source="strategy_runner",
        strategy_id=strategy_id,
        strategy_type=strategy_id,
        symbol=str(plan.get("symbol") or ""),
        timeframe=str(plan.get("timeframe") or ""),
        side=side,
        intent_status=intent_status,
        execution_mode="shadow_only",
        entry_type="observation_price",
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        rr_ratio=rr_ratio,
        risk_distance_pct=risk_dist,
        reward_distance_pct=reward_dist,
        max_risk_pct=max_risk_pct,
        notional_mode="fixed_risk_pct",
        position_size_preview=round(pos_size, 6),
        position_size_reason=pos_reason,
        source_priority=str(plan.get("plan_decision") or "WATCH"),
        source_watch_state=str(plan.get("source_status") or ""),
        source_reason=str(plan.get("reason") or ""),
        risk_gate_status=intent_status,
        risk_gate_reasons=risk_reasons,
        safety_flags=list(TRADE_INTENT_SAFETY_FLAGS),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _determine_status(
    side: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    rr_ratio: float,
    risk_dist: float,
    reward_dist: float,
    max_risk_pct: float,
) -> tuple[str, list[str]]:
    """Determine intent_status and reasons."""
    reasons = []

    if side == "NO_TRADE":
        return "INVALID", ["side is NO_TRADE"]

    if entry_price <= 0:
        return "INVALID", ["entry_price <= 0"]

    if stop_loss <= 0:
        return "BLOCKED_BY_RISK_GATE", ["stop_loss <= 0"]

    if take_profit <= 0:
        return "BLOCKED_BY_RISK_GATE", ["take_profit <= 0"]

    if rr_ratio < 1.5:
        reasons.append(f"rr_ratio {rr_ratio} < 1.5")

    if risk_dist <= 0:
        reasons.append("risk_distance_pct <= 0")
    elif risk_dist > 5.0:
        reasons.append(f"risk_distance_pct {risk_dist}% > 5.0%")

    if reward_dist > 0 and risk_dist > 0 and reward_dist <= risk_dist:
        reasons.append("reward_distance <= risk_distance")

    if max_risk_pct > 0.5:
        reasons.append(f"max_risk_pct {max_risk_pct}% > 0.5%")

    if side == "LONG":
        if stop_loss >= entry_price:
            reasons.append("LONG stop_loss must be below entry_price")
        if take_profit > 0 and take_profit <= entry_price:
            reasons.append("LONG take_profit must be above entry_price")
    elif side == "SHORT":
        if stop_loss <= entry_price:
            reasons.append("SHORT stop_loss must be above entry_price")
        if take_profit > 0 and take_profit >= entry_price:
            reasons.append("SHORT take_profit must be below entry_price")

    if reasons:
        return "BLOCKED_BY_RISK_GATE", reasons

    return "SHADOW_READY", []


def _calc_position_size(
    side: str,
    entry_price: float,
    stop_loss: float,
    paper_equity: float,
    max_risk_pct: float,
    intent_status: str,
) -> tuple[float, str]:
    """Calculate paper position size preview."""
    if intent_status != "SHADOW_READY":
        return 0.0, "not SHADOW_READY, no position preview"

    if entry_price <= 0 or stop_loss <= 0:
        return 0.0, "invalid entry or stop"

    risk_amount = paper_equity * max_risk_pct / 100.0
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit <= 0:
        return 0.0, "zero risk distance"

    size = risk_amount / risk_per_unit
    reason = (
        f"paper/shadow preview only. "
        f"equity={paper_equity}, risk={max_risk_pct}%, "
        f"risk_amount={risk_amount}, risk_per_unit={round(risk_per_unit, 6)}"
    )
    return size, reason
