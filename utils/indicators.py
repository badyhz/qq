import numpy as np


def ema(values, period: int) -> float:
    series = np.asarray(values, dtype=float)
    if len(series) == 0:
        return 0.0
    if len(series) < period:
        return float(series.mean())
    alpha = 2.0 / (period + 1)
    result = series[0]
    for value in series[1:]:
        result = alpha * value + (1 - alpha) * result
    return float(result)


def rolling_mean(values, period: int) -> float:
    series = np.asarray(values[-period:], dtype=float)
    if len(series) == 0:
        return 0.0
    return float(series.mean())


def rolling_std(values, period: int) -> float:
    series = np.asarray(values[-period:], dtype=float)
    if len(series) == 0:
        return 0.0
    return float(series.std(ddof=0))


def vwap(closes, volumes, period: int) -> float:
    close_arr = np.asarray(closes[-period:], dtype=float)
    volume_arr = np.asarray(volumes[-period:], dtype=float)
    if len(close_arr) == 0:
        return 0.0
    denominator = volume_arr.sum()
    if denominator == 0:
        return float(close_arr.mean())
    return float((close_arr * volume_arr).sum() / denominator)


def atr(highs, lows, closes, period: int) -> float:
    high_arr = np.asarray(highs, dtype=float)
    low_arr = np.asarray(lows, dtype=float)
    close_arr = np.asarray(closes, dtype=float)
    if len(close_arr) < 2:
        return float(max(high_arr[-1] - low_arr[-1], 0.0)) if len(close_arr) else 0.0

    true_ranges = []
    start_index = max(1, len(close_arr) - period + 1)
    for index in range(start_index, len(close_arr)):
        prev_close = close_arr[index - 1]
        high = high_arr[index]
        low = low_arr[index]
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))

    if not true_ranges:
        return 0.0
    return float(np.mean(true_ranges))
