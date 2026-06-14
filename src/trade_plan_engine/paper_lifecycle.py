"""Paper position lifecycle simulation."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass
from datetime import datetime, timezone

from src.trade_plan_engine.models import PaperPosition, new_id, utc_now_iso

MAX_HOLD_BARS = 48


@dataclass(frozen=True)
class LifecycleResult:
    lifecycle_id: str
    created_at: str
    positions: tuple[PaperPosition, ...]
    total_simulated: int
    final_verdict: str

    def to_dict(self) -> dict:
        return {
            "lifecycle_id": self.lifecycle_id,
            "created_at": self.created_at,
            "positions": [p.to_dict() for p in self.positions],
            "total_simulated": self.total_simulated,
            "final_verdict": self.final_verdict,
        }


def simulate_lifecycle(
    position: PaperPosition,
    ohlcv: list[dict],
    max_hold_bars: int = MAX_HOLD_BARS,
) -> PaperPosition:
    entry_low = position.paper_entry_price * 0.995
    entry_high = position.paper_entry_price * 1.005
    entered = False
    entry_bar = 0
    entry_time = ""

    bars = 0
    for bar in ohlcv:
        high = float(bar.get("high", 0))
        low = float(bar.get("low", 0))
        bar_time = bar.get("time", bar.get("timestamp", str(bars)))

        if not entered:
            if high >= entry_low and low <= entry_high:
                entered = True
                entry_bar = bars
                entry_time = str(bar_time)
                position.status = "PAPER_OPEN"
                position.paper_entry_time = entry_time
        else:
            bars_held = bars - entry_bar

            # Conservative: stop loss checked first
            if low <= position.paper_stop_loss:
                position.status = "PAPER_STOPPED"
                position.paper_exit_price = position.paper_stop_loss
                position.paper_exit_time = str(bar_time)
                position.paper_exit_reason = "stop_loss_hit"
                position.bars_held = bars_held
                r = position.paper_entry_price - position.paper_stop_loss
                if r > 0:
                    position.paper_pnl_r = -1.0
                    position.paper_pnl_pct = ((position.paper_stop_loss - position.paper_entry_price) / position.paper_entry_price) * 100
                return position

            if high >= position.paper_take_profit_3:
                position.status = "PAPER_CLOSED"
                position.paper_exit_price = position.paper_take_profit_3
                position.paper_exit_time = str(bar_time)
                position.paper_exit_reason = "tp3_hit"
                position.bars_held = bars_held
                r = position.paper_entry_price - position.paper_stop_loss
                if r > 0:
                    position.paper_pnl_r = 4.0
                    position.paper_pnl_pct = ((position.paper_take_profit_3 - position.paper_entry_price) / position.paper_entry_price) * 100
                return position

            if high >= position.paper_take_profit_2:
                position.status = "PAPER_TP2_HIT"

            if high >= position.paper_take_profit_1:
                if position.status != "PAPER_TP2_HIT":
                    position.status = "PAPER_TP1_HIT"

            if bars_held >= max_hold_bars and position.status not in ("PAPER_TP2_HIT",):
                position.status = "PAPER_TIME_STOPPED"
                position.paper_exit_price = high  # exit at bar high as approximation
                position.paper_exit_time = str(bar_time)
                position.paper_exit_reason = "time_stop"
                position.bars_held = bars_held
                r = position.paper_entry_price - position.paper_stop_loss
                if r > 0:
                    position.paper_pnl_r = (high - position.paper_entry_price) / r
                    position.paper_pnl_pct = ((high - position.paper_entry_price) / position.paper_entry_price) * 100
                return position

        bars += 1

    # Still open after all bars
    if entered:
        position.bars_held = bars - entry_bar
    return position


def run_lifecycle_batch(
    positions: list[PaperPosition],
    ohlcv_map: dict[str, list[dict]],
) -> LifecycleResult:
    results: list[PaperPosition] = []
    for pos in positions:
        ohlcv = ohlcv_map.get(pos.symbol, [])
        if ohlcv:
            result = simulate_lifecycle(pos, ohlcv)
        else:
            result = pos  # no data, stays PLANNED
        results.append(result)

    return LifecycleResult(
        lifecycle_id=new_id("LC"),
        created_at=utc_now_iso(),
        positions=tuple(results),
        total_simulated=len(results),
        final_verdict=f"PAPER_POSITION_LIFECYCLE_READY|SIMULATED={len(results)}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def write_result(result: LifecycleResult, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


def render_report(result: LifecycleResult) -> str:
    lines = ["# Paper Position Lifecycle", "",
        f"**lifecycle_id={result.lifecycle_id}**",
        f"**total_simulated={result.total_simulated}**", "",
        "## Positions", "",
        "| Symbol | Status | Entry | Exit | PnL(R) | Bars |",
        "|--------|--------|-------|------|--------|------|"]
    for p in result.positions:
        lines.append(
            f"| {p.symbol} | {p.status} | {p.paper_entry_price} | "
            f"{p.paper_exit_price} | {p.paper_pnl_r:.2f} | {p.bars_held} |")
    lines.extend(["", "## Conclusion", "", result.final_verdict, ""])
    return "\n".join(lines)
