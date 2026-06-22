"""Paper position simulator — converts SHADOW_READY intents to paper positions.

Two modes:
- intent_only: just open positions from intents, no market data
- public_readonly_update: update positions with real kline data (SL/TP check)

Future-only lifecycle: only bars after opened_bar_time can trigger TP/SL.
Same-intent dedup: no duplicate positions for the same intent_id.
Open position overlap guard: no duplicate OPEN for same strategy+symbol+tf+side.
Closed positions are never reopened.

No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from core.paper_trading.paper_position import (
    open_position, dict_to_position, PaperPosition, CLOSED_STATUSES,
)
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
    lifecycle_stats: dict[str, Any]
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
            "lifecycle_stats": self.lifecycle_stats,
            "safety_flags": list(self.safety_flags),
        }


def simulate_intent_only(
    intents: list[dict[str, Any]],
    date_str: str,
    existing_positions: Optional[list[dict[str, Any]]] = None,
    paper_equity: float = 10000.0,
) -> SimulationResult:
    """Open paper positions from SHADOW_READY intents. No market data.

    Deduplicates against existing positions by intent_id.
    """
    existing = existing_positions or []
    existing_intent_ids = {p.get("intent_id") for p in existing}
    overlap_keys = _build_overlap_keys(existing)

    positions: list[dict[str, Any]] = []
    new_count = 0
    deduped = 0
    invalid_count = 0
    skipped_overlap = 0
    skipped_overlap_details: list[dict[str, Any]] = []

    for intent in intents:
        intent_id = intent.get("intent_id", "")

        # Dedup: skip if already have a position for this intent
        if intent_id in existing_intent_ids:
            deduped += 1
            continue

        # Overlap guard: skip if same strategy+symbol+tf+side OPEN exists
        okey = _intent_overlap_key(intent)
        if okey in overlap_keys:
            skipped_overlap += 1
            skipped_overlap_details.append({
                "intent_id": intent_id,
                "strategy_id": intent.get("strategy_id", ""),
                "symbol": intent.get("symbol", ""),
                "timeframe": intent.get("timeframe", ""),
                "side": intent.get("side", ""),
                "reason": "existing_open_position_overlap",
            })
            continue

        pos = open_position(intent, paper_equity)
        if pos is None:
            invalid_count += 1
            continue

        positions.append(pos.to_dict())
        new_count += 1

    # Combine existing + new
    all_positions = existing + positions
    counts = _count_statuses(all_positions)

    return SimulationResult(
        date=date_str,
        mode="intent_only",
        position_count=len(all_positions),
        open_count=counts["OPEN"],
        tp_hit_count=counts["TAKE_PROFIT_HIT"],
        sl_hit_count=counts["STOP_LOSS_HIT"],
        timeout_count=counts["TIMEOUT_EXIT"],
        invalid_count=invalid_count,
        positions=all_positions,
        summary=_build_summary(all_positions),
        lifecycle_stats={
            "new_positions_count": new_count,
            "existing_positions_count": len(existing),
            "deduped_intents_count": deduped,
            "positions_updated_count": 0,
            "positions_skipped_no_future_bars": 0,
            "positions_skipped_newly_opened": 0,
            "positions_skipped_overlap_open": skipped_overlap,
            "skipped_overlap_intents": skipped_overlap_details,
            "overlap_guard_enabled": True,
            "overlap_keys_count": len(overlap_keys),
            "future_only": True,
            "allow_update_newly_opened": False,
        },
        safety_flags=list(POSITION_SAFETY_FLAGS),
    )


def simulate_with_klines(
    intents: list[dict[str, Any]],
    bars_by_symbol_tf: dict[str, list[MarketBar]],
    date_str: str,
    existing_positions: Optional[list[dict[str, Any]]] = None,
    paper_equity: float = 10000.0,
    timeout_bars: int = 24,
    future_only: bool = True,
    allow_update_newly_opened: bool = False,
    newly_opened_ids: Optional[set[str]] = None,
) -> SimulationResult:
    """Open positions and update with kline data to check TP/SL.

    future_only: only bars after opened_bar_time can trigger TP/SL.
    allow_update_newly_opened: if False, newly opened positions stay OPEN.
    """
    existing = existing_positions or []
    existing_intent_ids = {p.get("intent_id") for p in existing}
    overlap_keys = _build_overlap_keys(existing)
    newly_opened = newly_opened_ids or set()

    new_positions: list[dict[str, Any]] = []
    deduped = 0
    invalid_count = 0
    skipped_overlap = 0
    skipped_overlap_details: list[dict[str, Any]] = []

    # Open new positions from intents
    for intent in intents:
        intent_id = intent.get("intent_id", "")
        if intent_id in existing_intent_ids:
            deduped += 1
            continue

        # Overlap guard: skip if same strategy+symbol+tf+side OPEN exists
        okey = _intent_overlap_key(intent)
        if okey in overlap_keys:
            skipped_overlap += 1
            skipped_overlap_details.append({
                "intent_id": intent_id,
                "strategy_id": intent.get("strategy_id", ""),
                "symbol": intent.get("symbol", ""),
                "timeframe": intent.get("timeframe", ""),
                "side": intent.get("side", ""),
                "reason": "existing_open_position_overlap",
            })
            continue

        pos = open_position(intent, paper_equity)
        if pos is None:
            invalid_count += 1
            continue

        new_positions.append(pos.to_dict())
        newly_opened.add(pos.position_id)

    # Combine existing + new for update
    all_positions = existing + new_positions
    updated_count = 0
    skipped_no_future = 0
    skipped_newly = 0

    # Update positions with klines
    result_positions = []
    for pos_dict in all_positions:
        status = pos_dict.get("status", "OPEN")

        # Closed positions stay closed
        if status in CLOSED_STATUSES:
            result_positions.append(pos_dict)
            continue

        # Skip newly opened unless allowed
        pid = pos_dict.get("position_id", "")
        if pid in newly_opened and not allow_update_newly_opened:
            skipped_newly += 1
            result_positions.append(pos_dict)
            continue

        # Get bars for this symbol/timeframe
        sym = pos_dict.get("symbol", "")
        tf = pos_dict.get("timeframe", "")
        key = f"{sym}_{tf}"
        bars = bars_by_symbol_tf.get(key, [])

        if not bars:
            result_positions.append(pos_dict)
            continue

        # Filter to future-only bars
        opened_bar_time = pos_dict.get("opened_bar_time")
        if future_only and opened_bar_time is not None:
            future_bars = _future_bars_after_open(bars, opened_bar_time)
        elif future_only and opened_bar_time is None:
            # Missing opened_bar_time — skip update
            skipped_no_future += 1
            result_positions.append(pos_dict)
            continue
        else:
            future_bars = bars

        if not future_bars:
            skipped_no_future += 1
            result_positions.append(pos_dict)
            continue

        # Reconstruct PaperPosition for update
        pos = dict_to_position(pos_dict)
        updated = _update_position(pos, future_bars, timeout_bars)
        result_positions.append(updated)
        updated_count += 1

    counts = _count_statuses(result_positions)

    return SimulationResult(
        date=date_str,
        mode="public_readonly_update",
        position_count=len(result_positions),
        open_count=counts["OPEN"],
        tp_hit_count=counts["TAKE_PROFIT_HIT"],
        sl_hit_count=counts["STOP_LOSS_HIT"],
        timeout_count=counts["TIMEOUT_EXIT"],
        invalid_count=invalid_count,
        positions=result_positions,
        summary=_build_summary(result_positions),
        lifecycle_stats={
            "new_positions_count": len(new_positions),
            "existing_positions_count": len(existing),
            "deduped_intents_count": deduped,
            "positions_updated_count": updated_count,
            "positions_skipped_no_future_bars": skipped_no_future,
            "positions_skipped_newly_opened": skipped_newly,
            "positions_skipped_overlap_open": skipped_overlap,
            "skipped_overlap_intents": skipped_overlap_details,
            "overlap_guard_enabled": True,
            "overlap_keys_count": len(overlap_keys),
            "future_only": future_only,
            "allow_update_newly_opened": allow_update_newly_opened,
        },
        safety_flags=list(POSITION_SAFETY_FLAGS),
    )


def simulate_existing_positions_update_only(
    existing_positions: list[dict[str, Any]],
    bars_by_symbol_tf: dict[str, list[MarketBar]],
    date_str: str,
    timeout_bars: int = 24,
    future_only: bool = True,
) -> SimulationResult:
    """Update only existing OPEN positions. Never creates new positions.

    Used for position management without new signal scanning.
    """
    all_positions = list(existing_positions)
    updated_count = 0
    skipped_no_future = 0
    skipped_closed = 0
    skipped_missing_bars = 0

    result_positions = []
    for pos_dict in all_positions:
        status = pos_dict.get("status", "OPEN")

        # Closed positions stay closed
        if status in CLOSED_STATUSES:
            skipped_closed += 1
            result_positions.append(pos_dict)
            continue

        # Get bars for this symbol/timeframe
        sym = pos_dict.get("symbol", "")
        tf = pos_dict.get("timeframe", "")
        key = f"{sym}_{tf}"
        bars = bars_by_symbol_tf.get(key, [])

        if not bars:
            skipped_missing_bars += 1
            result_positions.append(pos_dict)
            continue

        # Filter to future-only bars
        opened_bar_time = pos_dict.get("opened_bar_time")
        if future_only and opened_bar_time is not None:
            future_bars = _future_bars_after_open(bars, opened_bar_time)
        elif future_only and opened_bar_time is None:
            skipped_no_future += 1
            result_positions.append(pos_dict)
            continue
        else:
            future_bars = bars

        if not future_bars:
            skipped_no_future += 1
            result_positions.append(pos_dict)
            continue

        # Reconstruct PaperPosition for update
        pos = dict_to_position(pos_dict)
        updated = _update_position(pos, future_bars, timeout_bars)
        result_positions.append(updated)
        updated_count += 1

    counts = _count_statuses(result_positions)

    return SimulationResult(
        date=date_str,
        mode="update_only",
        position_count=len(result_positions),
        open_count=counts["OPEN"],
        tp_hit_count=counts["TAKE_PROFIT_HIT"],
        sl_hit_count=counts["STOP_LOSS_HIT"],
        timeout_count=counts["TIMEOUT_EXIT"],
        invalid_count=0,
        positions=result_positions,
        summary=_build_summary(result_positions),
        lifecycle_stats={
            "new_positions_count": 0,
            "existing_positions_count": len(all_positions),
            "deduped_intents_count": 0,
            "positions_updated_count": updated_count,
            "positions_skipped_no_future_bars": skipped_no_future,
            "positions_skipped_newly_opened": 0,
            "positions_skipped_overlap_open": 0,
            "skipped_overlap_intents": [],
            "overlap_guard_enabled": True,
            "overlap_keys_count": 0,
            "positions_skipped_closed": skipped_closed,
            "positions_skipped_missing_bars": skipped_missing_bars,
            "update_only": True,
            "future_only": future_only,
            "allow_update_newly_opened": False,
        },
        safety_flags=list(POSITION_SAFETY_FLAGS),
    )


def _normalize_epoch_seconds(value: Any) -> Optional[float]:
    """Normalize epoch seconds/milliseconds/microseconds to seconds."""
    if value is None:
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    if ts > 1e15:
        return ts / 1_000_000
    if ts > 1e12:
        return ts / 1_000
    return ts


def _future_bars_after_open(bars: list[MarketBar], opened_bar_time: Any) -> list[MarketBar]:
    opened_ts = _normalize_epoch_seconds(opened_bar_time)
    if opened_ts is None:
        return []
    future_bars: list[MarketBar] = []
    for bar in bars:
        bar_ts = _normalize_epoch_seconds(bar.timestamp)
        if bar_ts is not None and bar_ts > opened_ts:
            future_bars.append(bar)
    return future_bars


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
                "last_checked_at": now,
                "last_checked_bar_time": bar.timestamp,
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
                "last_checked_at": now,
                "last_checked_bar_time": bar.timestamp,
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
                "last_checked_at": now,
                "last_checked_bar_time": bar.timestamp,
            })
            return result

    # Still open
    if bars:
        last_bar = bars[-1]
        last_close = last_bar.close
        pnl = _calc_pnl(side, entry, last_close, size)
        result = pos.to_dict()
        result["unrealized_pnl"] = round(pnl, 8)
        result["last_checked_at"] = now
        result["last_checked_bar_time"] = last_bar.timestamp
        return result

    return pos.to_dict()


def _calc_pnl(side: str, entry: float, exit_price: float, size: float) -> float:
    if side == "LONG":
        return (exit_price - entry) * size
    elif side == "SHORT":
        return (entry - exit_price) * size
    return 0.0


def _count_statuses(positions: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"OPEN": 0, "TAKE_PROFIT_HIT": 0, "STOP_LOSS_HIT": 0, "TIMEOUT_EXIT": 0, "INVALID": 0}
    for p in positions:
        s = p.get("status", "OPEN")
        if s in counts:
            counts[s] += 1
    return counts


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


def _build_overlap_keys(positions: list[dict[str, Any]]) -> set[str]:
    """Build set of overlap keys from OPEN positions."""
    keys = set()
    for p in positions:
        if p.get("status", "OPEN") == "OPEN":
            key = f"{p.get('strategy_id', '')}|{p.get('symbol', '')}|{p.get('timeframe', '')}|{p.get('side', '')}"
            keys.add(key)
    return keys


def _intent_overlap_key(intent: dict[str, Any]) -> str:
    """Build overlap key from an intent."""
    return f"{intent.get('strategy_id', '')}|{intent.get('symbol', '')}|{intent.get('timeframe', '')}|{intent.get('side', '')}"
