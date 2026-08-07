"""No-lookahead higher-timeframe trend alignment for composite strategy research.

The lower-timeframe decision at bar ``i`` may only consume higher-timeframe
bars whose close boundary is <= the lower bar's close boundary.  The actual
trend classification reuses the existing readonly signal analyzer instead of
introducing another trend engine.
"""
from __future__ import annotations

from typing import Sequence

from core.historical_ohlcv_schema import HistoricalBar
from core.paper_trading.data_source import MarketBar
from core.paper_trading.indicator_composite_strategy import HigherTimeframeTrend
from core.paper_trading.readonly_signal_analyzer import analyze_bars


_INTERVAL_SECONDS = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
}


def timeframe_seconds(timeframe: str) -> int:
    try:
        return _INTERVAL_SECONDS[str(timeframe).lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported timeframe: {timeframe}") from exc


def historical_to_market_bar(bar: HistoricalBar) -> MarketBar:
    return MarketBar(
        timestamp=float(bar.timestamp),
        open=float(bar.open),
        high=float(bar.high),
        low=float(bar.low),
        close=float(bar.close),
        volume=float(bar.volume),
        symbol=str(bar.symbol),
        timeframe=str(bar.timeframe),
    )


def _map_trend_bias(value: str) -> HigherTimeframeTrend:
    if value == "BULLISH":
        return HigherTimeframeTrend.UP
    if value == "BEARISH":
        return HigherTimeframeTrend.DOWN
    return HigherTimeframeTrend.NEUTRAL


def align_higher_timeframe_trends(
    lower_bars: Sequence[HistoricalBar],
    higher_bars: Sequence[HistoricalBar],
    *,
    analyzer_limit: int = 120,
) -> tuple[HigherTimeframeTrend, ...]:
    """Return one no-lookahead HTF trend value per lower-timeframe bar.

    A higher bar is eligible only after its full interval has elapsed.  Before
    30 eligible higher bars exist, the existing analyzer returns DATA_REJECT;
    that condition maps conservatively to NEUTRAL rather than fabricating a
    trend.
    """
    if analyzer_limit < 30:
        raise ValueError("analyzer_limit must be >= 30")
    if not lower_bars:
        return ()
    if not higher_bars:
        return tuple(HigherTimeframeTrend.NEUTRAL for _ in lower_bars)

    lower_tf = str(lower_bars[0].timeframe)
    higher_tf = str(higher_bars[0].timeframe)
    lower_interval = timeframe_seconds(lower_tf)
    higher_interval = timeframe_seconds(higher_tf)
    if higher_interval <= lower_interval:
        raise ValueError("higher timeframe must be strictly larger than lower timeframe")
    if any(str(bar.timeframe) != lower_tf for bar in lower_bars):
        raise ValueError("lower_bars contain mixed timeframes")
    if any(str(bar.timeframe) != higher_tf for bar in higher_bars):
        raise ValueError("higher_bars contain mixed timeframes")

    sorted_higher = sorted(higher_bars, key=lambda bar: float(bar.timestamp))
    eligible_market: list[MarketBar] = []
    next_higher = 0
    output: list[HigherTimeframeTrend] = []

    for lower in lower_bars:
        decision_cutoff = float(lower.timestamp) + lower_interval
        while next_higher < len(sorted_higher):
            candidate = sorted_higher[next_higher]
            candidate_close = float(candidate.timestamp) + higher_interval
            if candidate_close > decision_cutoff:
                break
            eligible_market.append(historical_to_market_bar(candidate))
            next_higher += 1

        if not eligible_market:
            output.append(HigherTimeframeTrend.NEUTRAL)
            continue
        analysis = analyze_bars(eligible_market[-analyzer_limit:])
        if analysis is None or analysis.watch_state == "DATA_REJECT":
            output.append(HigherTimeframeTrend.NEUTRAL)
        else:
            output.append(_map_trend_bias(analysis.trend_bias))

    return tuple(output)
