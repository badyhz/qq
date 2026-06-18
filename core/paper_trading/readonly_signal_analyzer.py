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
    # Watch state fields
    watch_state: str = "NEUTRAL"  # LONG_READY / LONG_WATCH / NEAR_TURN_UP / SHORT_WATCH / WEAK_AVOID / CHOPPY_AVOID / DATA_REJECT
    setup_type: str = "NO_TRADE"  # LONG_BREAKOUT / LONG_PULLBACK / MACD_TURNING_UP / OVERSOLD_REBOUND / SHORT_CONTINUATION / WEAK_TREND / NO_TRADE
    turning_score: int = 0        # 0-100
    weakness_score: int = 0       # 0-100
    risk_score: int = 0           # 0-100
    distance_to_invalidation_pct: float = 0.0
    distance_to_recent_high_pct: float = 0.0
    distance_to_recent_low_pct: float = 0.0
    atr_value: float = 0.0


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
            watch_state="DATA_REJECT", setup_type="NO_TRADE",
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
        elif curr_hist < 0 and curr_hist > prev_hist:
            macd_state = "HIST_SHRINKING_RED"
        elif curr_hist > 0 and curr_hist < prev_hist:
            macd_state = "HIST_SHRINKING_GREEN"

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

    # Recent high/low (last 50 bars)
    lookback = min(50, len(bars))
    recent_high = max(b.high for b in bars[-lookback:])
    recent_low = min(b.low for b in bars[-lookback:])

    # Distance percentages
    dist_inv_pct = ((last_close - invalidation_level) / last_close * 100) if last_close > 0 else 0.0
    dist_high_pct = ((recent_high - last_close) / last_close * 100) if last_close > 0 else 0.0
    dist_low_pct = ((last_close - recent_low) / last_close * 100) if last_close > 0 else 0.0

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

    # --- Watch state determination ---
    watch_state, setup_type, turning_score, weakness_score, risk_score = _determine_watch_state(
        trend_bias=trend_bias,
        macd_state=macd_state,
        rsi_state=rsi_state,
        rsi_val=rsi_val,
        volume_state=volume_state,
        bullish_signals=bullish_signals,
        bearish_signals=bearish_signals,
        ema12_last=ema12_last,
        ema26_last=ema26_last,
        last_close=last_close,
        dist_low_pct=dist_low_pct,
        dist_inv_pct=dist_inv_pct,
        priority=priority,
    )

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
        watch_state=watch_state,
        setup_type=setup_type,
        turning_score=turning_score,
        weakness_score=weakness_score,
        risk_score=risk_score,
        distance_to_invalidation_pct=round(dist_inv_pct, 2),
        distance_to_recent_high_pct=round(dist_high_pct, 2),
        distance_to_recent_low_pct=round(dist_low_pct, 2),
        atr_value=round(atr_val, 8),
    )


def _determine_watch_state(
    trend_bias, macd_state, rsi_state, rsi_val, volume_state,
    bullish_signals, bearish_signals,
    ema12_last, ema26_last, last_close,
    dist_low_pct, dist_inv_pct, priority,
):
    """Determine watch_state, setup_type, and scores."""
    turning_score = 0
    weakness_score = 0
    risk_score = 0

    # Turning score: how close to turning bullish
    if macd_state == "HIST_SHRINKING_RED":
        turning_score += 35
    elif macd_state == "BULLISH_CROSS":
        turning_score += 50
    elif macd_state == "HIST_EXPANDING_GREEN":
        turning_score += 40
    if rsi_state == "OVERSOLD":
        turning_score += 20
    elif 30 < rsi_val < 45:
        turning_score += 10
    if trend_bias == "NEUTRAL":
        turning_score += 10
    elif trend_bias == "BULLISH":
        turning_score += 20
    if dist_low_pct < 2.0:
        turning_score += 10  # Near recent low, potential bounce
    turning_score = min(turning_score, 100)

    # Weakness score: how weak/bearish
    if macd_state in ("BEARISH_CROSS", "HIST_EXPANDING_RED"):
        weakness_score += 30
    if trend_bias == "BEARISH":
        weakness_score += 25
    if rsi_val < 40:
        weakness_score += 15
    elif rsi_val > 60:
        weakness_score -= 10
    if volume_state == "NORMAL" and trend_bias == "BEARISH":
        weakness_score += 10
    weakness_score = max(0, min(weakness_score, 100))

    # Risk score: distance to invalidation (lower = riskier)
    if dist_inv_pct > 5:
        risk_score = 20
    elif dist_inv_pct > 3:
        risk_score = 40
    elif dist_inv_pct > 1.5:
        risk_score = 60
    elif dist_inv_pct > 0.5:
        risk_score = 80
    else:
        risk_score = 95

    # Determine watch state
    if priority == "REJECT":
        return "DATA_REJECT", "NO_TRADE", turning_score, weakness_score, risk_score

    # EMA tangled check (choppy)
    ema_spread = abs(ema12_last - ema26_last) / ema26_last * 100 if ema26_last and ema26_last > 0 else 0
    is_choppy = ema_spread < 0.3 and macd_state in ("NEUTRAL",) and volume_state == "NORMAL"

    if is_choppy:
        return "CHOPPY_AVOID", "NO_TRADE", turning_score, weakness_score, risk_score

    # LONG_READY
    if (trend_bias == "BULLISH" and
        macd_state in ("BULLISH_CROSS", "HIST_EXPANDING_GREEN") and
        rsi_state != "OVERBOUGHT" and
        bearish_signals == 0):
        setup = "LONG_BREAKOUT" if macd_state == "BULLISH_CROSS" else "LONG_PULLBACK"
        return "LONG_READY", setup, turning_score, weakness_score, risk_score

    # LONG_WATCH
    if (trend_bias in ("BULLISH", "NEUTRAL") and
        macd_state in ("HIST_EXPANDING_GREEN", "HIST_SHRINKING_RED") and
        rsi_state != "OVERBOUGHT"):
        return "LONG_WATCH", "LONG_PULLBACK", turning_score, weakness_score, risk_score

    # NEAR_TURN_UP
    if (trend_bias != "BEARISH" or macd_state in ("HIST_SHRINKING_RED",)) and \
       macd_state in ("HIST_SHRINKING_RED", "BULLISH_CROSS") and \
       rsi_state != "OVERBOUGHT" and dist_inv_pct > 1.0:
        return "NEAR_TURN_UP", "MACD_TURNING_UP", turning_score, weakness_score, risk_score

    if macd_state == "HIST_SHRINKING_RED" and rsi_val < 50 and dist_inv_pct > 1.5:
        return "NEAR_TURN_UP", "MACD_TURNING_UP", turning_score, weakness_score, risk_score

    # SHORT_WATCH
    if (trend_bias == "BEARISH" and
        macd_state in ("BEARISH_CROSS", "HIST_EXPANDING_RED") and
        rsi_state != "OVERSOLD"):
        return "SHORT_WATCH", "SHORT_CONTINUATION", turning_score, weakness_score, risk_score

    # WEAK_AVOID
    if weakness_score >= 40 and turning_score < 30:
        return "WEAK_AVOID", "WEAK_TREND", turning_score, weakness_score, risk_score

    # Default: LOW priority = WEAK_AVOID or SHORT_WATCH depending on weakness
    if bearish_signals >= 2:
        return "WEAK_AVOID", "WEAK_TREND", turning_score, weakness_score, risk_score

    return "CHOPPY_AVOID", "NO_TRADE", turning_score, weakness_score, risk_score
