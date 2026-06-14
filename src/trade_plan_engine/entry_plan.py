"""Entry plan generator for trade signals."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass
from datetime import datetime, timezone

from src.trade_plan_engine.models import SignalCandidate, TradePlan, new_id, utc_now_iso


def generate_entry_plan(signal: SignalCandidate) -> dict:
    price = signal.price
    entry_zone_low = round(price * 0.995, 8)
    entry_zone_high = round(price * 1.005, 8)

    confidence = "NORMAL"
    reasons = []

    if signal.signal_level == "B" and signal.above_ma99:
        entry_type = "BREAKOUT_OR_PULLBACK"
        reasons.append("signal_level=B and above_ma99")
    elif signal.signal_level == "B":
        entry_type = "PULLBACK"
        reasons.append("signal_level=B but below_ma99")
    else:
        entry_type = "WEAK_SIGNAL"
        confidence = "LOW"
        reasons.append(f"signal_level={signal.signal_level}")

    if signal.volume_ratio >= 1.5:
        confidence = "HIGH" if confidence == "NORMAL" else confidence
        reasons.append(f"volume_ratio={signal.volume_ratio:.2f}>=1.5")
    elif signal.volume_ratio < 1.0:
        confidence = "LOW"
        reasons.append(f"volume_ratio={signal.volume_ratio:.2f}<1.0")

    if signal.drop_pct < 2.0:
        confidence = "LOW"
        reasons.append(f"drop_pct={signal.drop_pct:.2f}%<2%")

    entry_reason = "; ".join(reasons) if reasons else "standard entry"
    entry_invalid_if = "price closes below ma25 or MACD histogram turns negative"
    entry_time_limit = "4h from signal time"

    return {
        "entry_type": entry_type,
        "entry_price": price,
        "entry_zone_low": entry_zone_low,
        "entry_zone_high": entry_zone_high,
        "confidence": confidence,
        "entry_reason": entry_reason,
        "entry_invalid_if": entry_invalid_if,
        "entry_time_limit": entry_time_limit,
    }
