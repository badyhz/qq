"""Paper position simulator — converts SHADOW_READY intents to paper positions.

Two modes:
- intent_only: just open positions from intents, no market data
- public_readonly_update: update positions with real kline data (SL/TP check)

No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from core.paper_trading.paper_position import open_position, PaperPosition
from core.paper_trading.data_source import MarketBar


@dataclass(frozen=True)
class SimulationResult:
    date: str
    mode: str
    position_count: int
    open_count: int
    tp_hit_count: int
    sl_hit_count: int
    timeout_count: int
    invalid_count: int
    positions: list[dict[str, Any]]
    summary: dict[str, Any]
    safety_flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "mode": self.mode,
            "position_count": self.position_count,
            "status_counts": {
                "OPEN": self.open_count,
                "TAKE_PROFIT_HIT": self.tp_hit_count,
                "STOP_LOSS_HIT": self.sl_hit_count,
                "TIMEOUT_EXIT": self.timeout_count,
                "INVALID": self.invalid_count,
            },
            "positions": self.positions,
            "summary": self.summary,
            "safety_flags": list(self.safety_flags),
        }


def simulate_intent_only(
    intents: list[dict[str, Any]],
    date_str: str,
    paper_equity: float = 10000.0,
) -> SimulationResult:
    """Open paper positions from SHADOW_READY intents. No market data."""
    positions: list[dict[str, Any]] = []
    open_count = 0
    tp_count = 0
    sl_count = 0
    timeout_count = 0
    invalid_count = 0

    for intent in intents:
        pos = open_position(intent, paper_equity)
        if pos is None:
            invalid_count += 1
            continue

        pos_dict = pos.to_dict()
        positions.append(pos_dict)
        if pos.status == "OPEN":
            open_count += 1

    return SimulationResult(
        date=date_str,
        mode="intent_only",
        position_count=len(positions),
        open_count=open_count,
        tp_hit_count=tp_count,
        sl_hit_count=sl_count,
        timeout_count=timeout_count,
        invalid_count=invalid_count,
        positions=positions,
        summary=_build_summary(positions),
        safety_flags=list(pos.safety_flags) if positions else [
            "PAPER_ONLY", "SHADOW_ONLY", "NO_ORDER", "POSITION_SIMULATION_ONLY",
        ],
    )


def simulate_with_klines(
    intents: list[dict[str, Any]],
    bars_by_symbol_tf: dict[str, list[MarketBar]],
    date_str: str,
    paper_equity: float = 10000.0,
    timeout_bars: int = 24,
) -> SimulationResult:
    """Open positions and update with kline data to check TP/SL."""
    positions: list[dict[str, Any]] = []
    open_count = 0
    tp_count = 0
    sl_count = 0
    timeout_count = 0
    invalid_count = 0

    for intent in intents:
        pos = open_position(intent, paper_equity)
        if pos is None:
            invalid_count += 1
            continue

        key = f"{pos.symbol}_{pos.timeframe}"
        bars = bars_by_symbol_tf.get(key, [])

        if bars:
            updated = _update_position(pos, bars, timeout_bars)
        else:
            updated = pos.to_dict()

        positions.append(updated)
        status = updated.get("status", "OPEN")
        if status == "OPEN":
            open_count += 1
        elif status == "TAKE_PROFIT_HIT":
            tp_count += 1
        elif status == "STOP_LOSS_HIT":
            sl_count += 1
        elif status == "TIMEOUT_EXIT":
            timeout_count += 1
        else:
            invalid_count += 1

    return SimulationResult(
        date=date_str,
        mode="public_readonly_update",
        position_count=len(positions),
        open_count=open_count,
        tp_hit_count=tp_count,
        sl_hit_count=sl_count,
        timeout_count=timeout_count,
        invalid_count=invalid_count,
        positions=positions,
        summary=_build_summary(positions),
        safety_flags=list(POSITION_SAFETY_FLAGS),
    )


def _update_position(
    pos: PaperPosition,
    bars: list[MarketBar],
    timeout_bars: int,
) -> dict[str, Any]:
    """Update a position with kline data. Returns updated position dict."""
    entry = pos.entry_price
    sl = pos.stop_loss
    tp = pos.take_profit
    side = pos.side
    size = pos.position_size_preview

    now = datetime.now(timezone.utc).isoformat()

    for i, bar in enumerate(bars):
        if i >= timeout_bars:
            # Timeout
            exit_price = bar.close
            pnl = _calc_pnl(side, entry, exit_price, size)
            risk_amount = abs(entry - sl) * size
            r_mult = pnl / risk_amount if risk_amount > 0 else 0.0

            result = pos.to_dict()
            result.update({
                "status": "TIMEOUT_EXIT",
                "closed_at": now,
                "exit_price": exit_price,
                "exit_reason": f"timeout after {timeout_bars} bars",
                "unrealized_pnl": 0.0,
                "realized_pnl": round(pnl, 8),
                "realized_pnl_pct": round(pnl / (entry * size) * 100, 4) if entry * size > 0 else 0.0,
                "r_multiple": round(r_mult, 4),
            })
            return result

        hit_sl = False
        hit_tp = False

        if side == "LONG":
            hit_sl = bar.low <= sl
            hit_tp = bar.high >= tp
        elif side == "SHORT":
            hit_sl = bar.high >= sl
            hit_tp = bar.low <= tp

        if hit_sl:
            # Conservative: SL takes priority
            exit_price = sl
            pnl = _calc_pnl(side, entry, exit_price, size)
            risk_amount = abs(entry - sl) * size
            r_mult = pnl / risk_amount if risk_amount > 0 else 0.0

            result = pos.to_dict()
            result.update({
                "status": "STOP_LOSS_HIT",
                "closed_at": now,
                "exit_price": exit_price,
                "exit_reason": "stop_loss triggered",
                "unrealized_pnl": 0.0,
                "realized_pnl": round(pnl, 8),
                "realized_pnl_pct": round(pnl / (entry * size) * 100, 4) if entry * size > 0 else 0.0,
                "r_multiple": round(r_mult, 4),
            })
            return result

        if hit_tp:
            exit_price = tp
            pnl = _calc_pnl(side, entry, exit_price, size)
            risk_amount = abs(entry - sl) * size
            r_mult = pnl / risk_amount if risk_amount > 0 else 0.0

            result = pos.to_dict()
            result.update({
                "status": "TAKE_PROFIT_HIT",
                "closed_at": now,
                "exit_price": exit_price,
                "exit_reason": "take_profit triggered",
                "unrealized_pnl": 0.0,
                "realized_pnl": round(pnl, 8),
                "realized_pnl_pct": round(pnl / (entry * size) * 100, 4) if entry * size > 0 else 0.0,
                "r_multiple": round(r_mult, 4),
            })
            return result

    # Still open — compute unrealized PnL from last bar
    if bars:
        last_close = bars[-1].close
        pnl = _calc_pnl(side, entry, last_close, size)
        result = pos.to_dict()
        result["unrealized_pnl"] = round(pnl, 8)
        return result

    return pos.to_dict()


def _calc_pnl(side: str, entry: float, exit_price: float, size: float) -> float:
    if side == "LONG":
        return (exit_price - entry) * size
    elif side == "SHORT":
        return (entry - exit_price) * size
    return 0.0


def _build_summary(positions: list[dict[str, Any]]) -> dict[str, Any]:
    """Build per-strategy summary."""
    by_strategy: dict[str, list[dict]] = {}
    for p in positions:
        sid = p.get("strategy_id", "unknown")
        by_strategy.setdefault(sid, []).append(p)

    summaries = {}
    for sid, pos_list in by_strategy.items():
        total = len(pos_list)
        tp = sum(1 for p in pos_list if p.get("status") == "TAKE_PROFIT_HIT")
        sl = sum(1 for p in pos_list if p.get("status") == "STOP_LOSS_HIT")
        opn = sum(1 for p in pos_list if p.get("status") == "OPEN")
        timeout = sum(1 for p in pos_list if p.get("status") == "TIMEOUT_EXIT")
        total_pnl = sum(p.get("realized_pnl", 0) for p in pos_list)
        avg_r = 0.0
        closed = [p for p in pos_list if p.get("r_multiple", 0) != 0]
        if closed:
            avg_r = sum(p.get("r_multiple", 0) for p in closed) / len(closed)

        summaries[sid] = {
            "total": total,
            "OPEN": opn,
            "TAKE_PROFIT_HIT": tp,
            "STOP_LOSS_HIT": sl,
            "TIMEOUT_EXIT": timeout,
            "total_realized_pnl": round(total_pnl, 8),
            "avg_r_multiple": round(avg_r, 4),
        }

    return {
        "by_strategy": summaries,
        "total_positions": len(positions),
    }


POSITION_SAFETY_FLAGS = [
    "PAPER_ONLY", "SHADOW_ONLY", "NO_ORDER", "NO_REAL_ORDER",
    "NO_ACCOUNT", "NO_SECRET", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_WEBHOOK_SEND", "POSITION_SIMULATION_ONLY",
]
