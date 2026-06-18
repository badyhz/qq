"""Paper position — shadow-only position from a SHADOW_READY trade intent.

No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


POSITION_SAFETY_FLAGS = [
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
    "POSITION_SIMULATION_ONLY",
]

CLOSED_STATUSES = {"TAKE_PROFIT_HIT", "STOP_LOSS_HIT", "TIMEOUT_EXIT", "INVALID"}


@dataclass(frozen=True)
class PaperPosition:
    """Shadow-only paper position. Never results in a real order."""
    position_id: str
    intent_id: str
    date: str
    source: str
    strategy_id: str
    strategy_type: str
    symbol: str
    timeframe: str
    side: str
    status: str
    entry_price: float
    stop_loss: float
    take_profit: float
    rr_ratio: float
    position_size_preview: float
    max_risk_pct: float
    paper_equity_preview: float
    opened_at: str
    opened_bar_time: Optional[int]
    closed_at: Optional[str]
    exit_price: Optional[float]
    exit_reason: Optional[str]
    unrealized_pnl: float
    realized_pnl: float
    realized_pnl_pct: float
    r_multiple: float
    source_trade_intent_status: str
    risk_gate_status: str
    lifecycle_mode: str
    last_checked_at: Optional[str]
    last_checked_bar_time: Optional[int]
    safety_flags: list[str]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_id": self.position_id,
            "intent_id": self.intent_id,
            "date": self.date,
            "source": self.source,
            "strategy_id": self.strategy_id,
            "strategy_type": self.strategy_type,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "side": self.side,
            "status": self.status,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "rr_ratio": self.rr_ratio,
            "position_size_preview": self.position_size_preview,
            "max_risk_pct": self.max_risk_pct,
            "paper_equity_preview": self.paper_equity_preview,
            "opened_at": self.opened_at,
            "opened_bar_time": self.opened_bar_time,
            "closed_at": self.closed_at,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "realized_pnl_pct": self.realized_pnl_pct,
            "r_multiple": self.r_multiple,
            "source_trade_intent_status": self.source_trade_intent_status,
            "risk_gate_status": self.risk_gate_status,
            "lifecycle_mode": self.lifecycle_mode,
            "last_checked_at": self.last_checked_at,
            "last_checked_bar_time": self.last_checked_bar_time,
            "safety_flags": list(self.safety_flags),
            "created_at": self.created_at,
        }


def open_position(intent: dict[str, Any], paper_equity: float = 10000.0) -> Optional[PaperPosition]:
    """Open a paper position from a SHADOW_READY trade intent.

    Returns None if intent is not SHADOW_READY or side is NO_TRADE.
    """
    intent_status = intent.get("intent_status")
    if intent_status != "SHADOW_READY":
        return None

    side = intent.get("side")
    if side not in ("LONG", "SHORT"):
        return None

    execution_mode = intent.get("execution_mode")
    if execution_mode != "shadow_only":
        return None

    now = datetime.now(timezone.utc).isoformat()
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    entry = float(intent.get("entry_price") or 0)
    sl = float(intent.get("stop_loss") or 0)
    tp = float(intent.get("take_profit") or 0)

    if entry <= 0 or sl <= 0 or tp <= 0:
        return None

    return PaperPosition(
        position_id=f"PP_{uuid.uuid4().hex[:12]}",
        intent_id=str(intent.get("intent_id") or ""),
        date=str(intent.get("date") or ""),
        source="trade_intent",
        strategy_id=str(intent.get("strategy_id") or ""),
        strategy_type=str(intent.get("strategy_type") or ""),
        symbol=str(intent.get("symbol") or ""),
        timeframe=str(intent.get("timeframe") or ""),
        side=side,
        status="OPEN",
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
        rr_ratio=float(intent.get("rr_ratio") or 0),
        position_size_preview=float(intent.get("position_size_preview") or 0),
        max_risk_pct=float(intent.get("max_risk_pct") or 0),
        paper_equity_preview=paper_equity,
        opened_at=now,
        opened_bar_time=now_ts,
        closed_at=None,
        exit_price=None,
        exit_reason=None,
        unrealized_pnl=0.0,
        realized_pnl=0.0,
        realized_pnl_pct=0.0,
        r_multiple=0.0,
        source_trade_intent_status=intent_status,
        risk_gate_status=str(intent.get("risk_gate_status") or ""),
        lifecycle_mode="future_only",
        last_checked_at=None,
        last_checked_bar_time=None,
        safety_flags=list(POSITION_SAFETY_FLAGS),
        created_at=now,
    )


def dict_to_position(d: dict[str, Any]) -> PaperPosition:
    """Reconstruct a PaperPosition from a dict (e.g. from JSON)."""
    return PaperPosition(
        position_id=d["position_id"],
        intent_id=d["intent_id"],
        date=d["date"],
        source=d["source"],
        strategy_id=d["strategy_id"],
        strategy_type=d["strategy_type"],
        symbol=d["symbol"],
        timeframe=d["timeframe"],
        side=d["side"],
        status=d["status"],
        entry_price=d["entry_price"],
        stop_loss=d["stop_loss"],
        take_profit=d["take_profit"],
        rr_ratio=d["rr_ratio"],
        position_size_preview=d["position_size_preview"],
        max_risk_pct=d["max_risk_pct"],
        paper_equity_preview=d["paper_equity_preview"],
        opened_at=d["opened_at"],
        opened_bar_time=d.get("opened_bar_time"),
        closed_at=d.get("closed_at"),
        exit_price=d.get("exit_price"),
        exit_reason=d.get("exit_reason"),
        unrealized_pnl=d.get("unrealized_pnl", 0.0),
        realized_pnl=d.get("realized_pnl", 0.0),
        realized_pnl_pct=d.get("realized_pnl_pct", 0.0),
        r_multiple=d.get("r_multiple", 0.0),
        source_trade_intent_status=d.get("source_trade_intent_status", ""),
        risk_gate_status=d.get("risk_gate_status", ""),
        lifecycle_mode=d.get("lifecycle_mode", "future_only"),
        last_checked_at=d.get("last_checked_at"),
        last_checked_bar_time=d.get("last_checked_bar_time"),
        safety_flags=d.get("safety_flags", list(POSITION_SAFETY_FLAGS)),
        created_at=d.get("created_at", ""),
    )
