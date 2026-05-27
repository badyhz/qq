"""Tests for offline backtest signal engine. 25+ tests."""

import pytest

from core.offline_backtest_signal_engine import (
    Signal,
    SignalType,
    apply_cooldown,
    check_min_body_pct,
    detect_breakout_signals,
    is_range_high_breakout,
)


class _P:
    """Minimal params for signal engine tests."""
    def __init__(self, lookback_bars=5, breakout_buffer_pct=0.003,
                 min_body_pct=0.3, cooldown_bars=3):
        self.lookback_bars = lookback_bars
        self.breakout_buffer_pct = breakout_buffer_pct
        self.min_body_pct = min_body_pct
        self.cooldown_bars = cooldown_bars


def _bar(high=105.0, low=95.0, open_=100.0, close=104.0, ts=0):
    return {"timestamp": ts, "open": open_, "high": high, "low": low, "close": close, "volume": 1.0}


def _make_trending_bars(n=20):
    """Create bars with a clear breakout pattern."""
    bars = []
    for i in range(n):
        if i < 10:
            # Range-bound
            bars.append(_bar(high=100.0 + (i % 3), low=95.0, open_=97.0, close=98.0, ts=i))
        else:
            # Breaking out
            bars.append(_bar(high=105.0 + (i - 10), low=98.0, open_=100.0, close=104.0 + (i - 10), ts=i))
    return bars


class TestSignalDataclass:
    def test_frozen(self):
        s = Signal(signal_id="s1", bar_index=5, signal_type=SignalType.LONG_BREAKOUT,
                   entry_price=100.0, timestamp=0, lookback_high=99.0, body_pct=0.5)
        with pytest.raises(AttributeError):
            s.bar_index = 6  # type: ignore

    def test_valid_construction(self):
        s = Signal(signal_id="s1", bar_index=5, signal_type=SignalType.LONG_BREAKOUT,
                   entry_price=100.0, timestamp=0, lookback_high=99.0, body_pct=0.5)
        assert s.signal_id == "s1"
        assert s.signal_type == SignalType.LONG_BREAKOUT

    def test_rejects_negative_bar_index(self):
        with pytest.raises(ValueError, match="bar_index"):
            Signal(signal_id="s1", bar_index=-1, signal_type=SignalType.LONG_BREAKOUT,
                   entry_price=100.0, timestamp=0, lookback_high=99.0, body_pct=0.5)

    def test_rejects_zero_entry_price(self):
        with pytest.raises(ValueError, match="entry_price"):
            Signal(signal_id="s1", bar_index=5, signal_type=SignalType.LONG_BREAKOUT,
                   entry_price=0.0, timestamp=0, lookback_high=99.0, body_pct=0.5)

    def test_rejects_zero_lookback_high(self):
        with pytest.raises(ValueError, match="lookback_high"):
            Signal(signal_id="s1", bar_index=5, signal_type=SignalType.LONG_BREAKOUT,
                   entry_price=100.0, timestamp=0, lookback_high=0.0, body_pct=0.5)


class TestIsRangeHighBreakout:
    def test_breakout_above_threshold(self):
        bar = _bar(high=105.0)
        assert is_range_high_breakout(bar, 100.0, 0.003) is True

    def test_no_breakout_below_threshold(self):
        bar = _bar(high=100.0)
        assert is_range_high_breakout(bar, 100.0, 0.01) is False

    def test_exact_threshold_not_breakout(self):
        # threshold = 100 * 1.01 = 101.0, high = 100.9
        bar = _bar(high=100.9)
        assert is_range_high_breakout(bar, 100.0, 0.01) is False

    def test_zero_lookback_high_returns_false(self):
        bar = _bar(high=105.0)
        assert is_range_high_breakout(bar, 0.0, 0.01) is False

    def test_zero_buffer_breakout(self):
        bar = _bar(high=100.0)
        # threshold = 100 * 1.0 = 100
        assert is_range_high_breakout(bar, 100.0, 0.0) is True

    def test_negative_lookback_returns_false(self):
        bar = _bar(high=105.0)
        assert is_range_high_breakout(bar, -1.0, 0.01) is False


class TestCheckMinBodyPct:
    def test_large_body_passes(self):
        bar = _bar(high=110.0, low=90.0, open_=95.0, close=105.0)
        # body = 10, range = 20, pct = 0.5
        assert check_min_body_pct(bar, 0.3) is True

    def test_small_body_fails(self):
        bar = _bar(high=110.0, low=90.0, open_=99.0, close=101.0)
        # body = 2, range = 20, pct = 0.1
        assert check_min_body_pct(bar, 0.3) is False

    def test_zero_range_returns_false(self):
        bar = _bar(high=100.0, low=100.0, open_=100.0, close=100.0)
        assert check_min_body_pct(bar, 0.3) is False

    def test_exact_threshold_passes(self):
        bar = _bar(high=100.0, low=90.0, open_=93.0, close=97.0)
        # body = 4, range = 10, pct = 0.4
        assert check_min_body_pct(bar, 0.4) is True

    def test_doji_bar_fails(self):
        bar = _bar(high=100.0, low=90.0, open_=95.0, close=95.0)
        # body = 0, pct = 0
        assert check_min_body_pct(bar, 0.01) is False


class TestDetectBreakoutSignals:
    def test_detects_obvious_breakout(self):
        bars = _make_trending_bars(20)
        params = _P(lookback_bars=5, breakout_buffer_pct=0.001, min_body_pct=0.2)
        signals = detect_breakout_signals(bars, params)
        assert len(signals) > 0

    def test_signal_type_is_long_breakout(self):
        bars = _make_trending_bars(20)
        params = _P(lookback_bars=5, breakout_buffer_pct=0.001, min_body_pct=0.2)
        signals = detect_breakout_signals(bars, params)
        for s in signals:
            assert s.signal_type == SignalType.LONG_BREAKOUT

    def test_no_signals_in_range_bound(self):
        # All bars have similar highs
        bars = [_bar(high=100.0, low=95.0, open_=97.0, close=98.0, ts=i) for i in range(20)]
        params = _P(lookback_bars=5, breakout_buffer_pct=0.01, min_body_pct=0.1)
        signals = detect_breakout_signals(bars, params)
        assert len(signals) == 0

    def test_signal_bar_index_in_range(self):
        bars = _make_trending_bars(20)
        params = _P(lookback_bars=5, breakout_buffer_pct=0.001, min_body_pct=0.2)
        signals = detect_breakout_signals(bars, params)
        for s in signals:
            assert s.bar_index >= params.lookback_bars
            assert s.bar_index < len(bars)

    def test_high_buffer_filters_signals(self):
        bars = _make_trending_bars(20)
        # Very high buffer should produce fewer signals
        low_buf = detect_breakout_signals(bars, _P(breakout_buffer_pct=0.001))
        high_buf = detect_breakout_signals(bars, _P(breakout_buffer_pct=0.1))
        assert len(high_buf) <= len(low_buf)

    def test_high_min_body_filters_signals(self):
        bars = _make_trending_bars(20)
        low_body = detect_breakout_signals(bars, _P(min_body_pct=0.1))
        high_body = detect_breakout_signals(bars, _P(min_body_pct=0.9))
        assert len(high_body) <= len(low_body)

    def test_signal_ids_sequential(self):
        bars = _make_trending_bars(20)
        params = _P(lookback_bars=5, breakout_buffer_pct=0.001, min_body_pct=0.2)
        signals = detect_breakout_signals(bars, params)
        for i, s in enumerate(signals):
            assert s.signal_id == f"sig_{i + 1}"

    def test_entry_price_is_close(self):
        bars = _make_trending_bars(20)
        params = _P(lookback_bars=5, breakout_buffer_pct=0.001, min_body_pct=0.2)
        signals = detect_breakout_signals(bars, params)
        for s in signals:
            assert s.entry_price == bars[s.bar_index]["close"]

    def test_empty_bars_returns_empty(self):
        signals = detect_breakout_signals([], _P())
        assert signals == []


class TestApplyCooldown:
    def test_no_cooldown_keeps_all(self):
        signals = [
            Signal(f"sig_{i}", i, SignalType.LONG_BREAKOUT, 100.0, i, 99.0, 0.5)
            for i in range(5)
        ]
        filtered = apply_cooldown(signals, cooldown_bars=0)
        assert len(filtered) == 5

    def test_cooldown_filters_close_signals(self):
        signals = [
            Signal(f"sig_{i}", i, SignalType.LONG_BREAKOUT, 100.0, i, 99.0, 0.5)
            for i in [0, 1, 2, 10, 11]
        ]
        filtered = apply_cooldown(signals, cooldown_bars=5)
        assert len(filtered) == 2
        assert filtered[0].bar_index == 0
        assert filtered[1].bar_index == 10

    def test_cooldown_empty_input(self):
        assert apply_cooldown([], cooldown_bars=5) == []

    def test_cooldown_negative_keeps_all(self):
        signals = [
            Signal(f"sig_{i}", i, SignalType.LONG_BREAKOUT, 100.0, i, 99.0, 0.5)
            for i in range(3)
        ]
        filtered = apply_cooldown(signals, cooldown_bars=-1)
        assert len(filtered) == 3

    def test_cooldown_preserves_first_signal(self):
        signals = [
            Signal("sig_0", 5, SignalType.LONG_BREAKOUT, 100.0, 5, 99.0, 0.5),
            Signal("sig_1", 6, SignalType.LONG_BREAKOUT, 100.0, 6, 99.0, 0.5),
        ]
        filtered = apply_cooldown(signals, cooldown_bars=10)
        assert len(filtered) == 1
        assert filtered[0].signal_id == "sig_0"
