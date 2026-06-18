"""Readonly signal analyzer — MACD/EMA/RSI/ATR/volume on MarketBar data. No network, no orders."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from core.paper_trading.data_source import MarketBar


@dataclass(frozen=True)
class SignalResult:
    symbol: str
    timeframe: str
    last_close: float
    trend_bias: str          # BULLISH / BEARISH / NEUTRAL
    macd_state: str          # BULLISH_CROSS / BEARISH_CROSS / HIST_EXPANDING_GREEN / HIST_EXPANDING_RED / NEUTRAL
    rsi_state: str           # OVERSOLD / NEUTRAL / OVERBOUGHT
    volume_state: str        # NORMAL / SPIKE
    priority: str            # HIGH / MEDIUM / LOW / REJECT
    entry_observation: float
    invalidation_level: float
    risk_notes: str
    reasons: List[str]


def _ema(values: List[float], period: int) -> List[Optional[float]]:
    """Calculate EMA. Returns list same length as input (None for insufficient data)."""
    if len(values) < period:
        return [None] * len(values)
    result: List[Optional[float]] = [None] * (period - 1)
    sma = sum(values[:period]) / period
    result.append(sma)
    k = 2.0 / (period + 1)
    for i in range(period, len(values)):
        prev = result[-1]
        if prev is None:
            result.append(values[i])
        else:
            result.append(values[i] * k + prev * (1 - k))
    return result


def _rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
    """Calculate RSI. Returns list same length as input."""
    if len(closes) < period + 1:
        return [None] * len(closes)
    result: List[Optional[float]] = [None] * period
    gains = []
    losses = []
    for i in range(1, period + 1):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100 - 100 / (1 + rs))
    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - 100 / (1 + rs))
    return result


def _atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[Optional[float]]:
    """Calculate ATR. Returns list same length as input."""
    if len(closes) < period + 1:
        return [None] * len(closes)
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    result: List[Optional[float]] = [None] * period
    atr_val = sum(trs[:period]) / period
    result.append(atr_val)
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
        result.append(atr_val)
    return result


def analyze_bars(bars: List[MarketBar]) -> Optional[SignalResult]:
    """Analyze a list of MarketBar and return a SignalResult."""
    if len(bars) < 30:
        return SignalResult(
            symbol=bars[0].symbol if bars else "",
            timeframe=bars[0].timeframe if bars else "",
            last_close=bars[-1].close if bars else 0.0,
            trend_bias="NEUTRAL", macd_state="NEUTRAL", rsi_state="NEUTRAL",
            volume_state="NORMAL", priority="REJECT",
            entry_observation=0.0, invalidation_level=0.0,
            risk_notes="too few bars",
            reasons=["REJECT: insufficient data (< 30 bars)"],
        )

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]

    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)

    macd_line: List[Optional[float]] = []
    for i in range(len(closes)):
        if ema12[i] is not None and ema26[i] is not None:
            macd_line.append(ema12[i] - ema26[i])
        else:
            macd_line.append(None)

    macd_signal = _ema([v for v in macd_line if v is not None], 9)
    # Re-align
    macd_signal_full: List[Optional[float]] = [None] * (len(macd_line) - len(macd_signal)) + macd_signal

    rsi_values = _rsi(closes, 14)
    atr_values = _atr(highs, lows, closes, 14)

    last = bars[-1]
    last_close = last.close

    # MACD state
    macd_state = "NEUTRAL"
    if len(macd_line) >= 3 and macd_line[-1] is not None and macd_line[-2] is not None:
        curr_hist = macd_line[-1] - (macd_signal_full[-1] or 0)
        prev_hist = macd_line[-2] - (macd_signal_full[-2] or 0)
        if macd_line[-2] < (macd_signal_full[-2] or 0) and macd_line[-1] > (macd_signal_full[-1] or 0):
            macd_state = "BULLISH_CROSS"
        elif macd_line[-2] > (macd_signal_full[-2] or 0) and macd_line[-1] < (macd_signal_full[-1] or 0):
            macd_state = "BEARISH_CROSS"
        elif curr_hist > 0 and curr_hist > prev_hist:
            macd_state = "HIST_EXPANDING_GREEN"
        elif curr_hist < 0 and curr_hist < prev_hist:
            macd_state = "HIST_EXPANDING_RED"

    # RSI state
    rsi_val = rsi_values[-1] if rsi_values[-1] is not None else 50.0
    if rsi_val <= 30:
        rsi_state = "OVERSOLD"
    elif rsi_val >= 70:
        rsi_state = "OVERBOUGHT"
    else:
        rsi_state = "NEUTRAL"

    # Volume state
    vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
    last_vol = volumes[-1]
    volume_state = "SPIKE" if last_vol > vol_avg * 1.5 else "NORMAL"

    # Trend bias
    ema12_last = ema12[-1]
    ema26_last = ema26[-1]
    if ema12_last is not None and ema26_last is not None:
        if ema12_last > ema26_last and last_close > ema12_last:
            trend_bias = "BULLISH"
        elif ema12_last < ema26_last and last_close < ema12_last:
            trend_bias = "BEARISH"
        else:
            trend_bias = "NEUTRAL"
    else:
        trend_bias = "NEUTRAL"

    # Risk distance
    atr_val = atr_values[-1] if atr_values[-1] is not None else 0.0
    invalidation_level = last_close - atr_val * 1.5 if atr_val > 0 else last_close * 0.97

    # Priority
    reasons = []
    priority = "LOW"

    if macd_state in ("BULLISH_CROSS", "HIST_EXPANDING_GREEN"):
        reasons.append(f"MACD {macd_state}")
    if trend_bias == "BULLISH":
        reasons.append("trend bullish")
    if rsi_state == "OVERSOLD":
        reasons.append("RSI oversold")
    if volume_state == "SPIKE":
        reasons.append("volume spike")

    bullish_signals = sum(1 for s in [macd_state in ("BULLISH_CROSS", "HIST_EXPANDING_GREEN"),
                                       trend_bias == "BULLISH",
                                       rsi_state == "OVERSOLD"] if s)

    bearish_signals = sum(1 for s in [macd_state in ("BEARISH_CROSS", "HIST_EXPANDING_RED"),
                                       trend_bias == "BEARISH",
                                       rsi_state == "OVERBOUGHT"] if s)

    if rsi_state == "OVERBOUGHT" and macd_state == "BEARISH_CROSS":
        priority = "REJECT"
        reasons.append("REJECT: overbought + bearish cross")
    elif bullish_signals >= 3:
        priority = "HIGH"
    elif bullish_signals >= 2:
        priority = "MEDIUM"
    elif bearish_signals >= 2:
        priority = "LOW"
        reasons.append("bearish alignment")
    else:
        priority = "LOW"

    if not reasons:
        reasons.append("no strong signal")

    risk_notes = f"ATR={atr_val:.2f}" if atr_val > 0 else "ATR unavailable"

    return SignalResult(
        symbol=last.symbol,
        timeframe=last.timeframe,
        last_close=last_close,
        trend_bias=trend_bias,
        macd_state=macd_state,
        rsi_state=rsi_state,
        volume_state=volume_state,
        priority=priority,
        entry_observation=last_close,
        invalidation_level=round(invalidation_level, 2),
        risk_notes=risk_notes,
        reasons=reasons,
    )
