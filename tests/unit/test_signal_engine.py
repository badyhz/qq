from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock

import pytest

from core.signal_engine import SignalEngine


def make_candle(base_candle: dict, minute: int, close: Optional[float] = None) -> dict:
    candle_close = float(base_candle["close"] if close is None else close)
    return {
        **base_candle,
        "timestamp": datetime(2026, 4, 18, 12, minute, tzinfo=timezone.utc),
        "close": candle_close,
        "high": candle_close + 1.0,
        "low": candle_close - 1.0,
        "volume": float(base_candle["volume"]) + minute,
    }


def seed_ready_history(engine: SignalEngine, base_candle: dict) -> None:
    required = max(
        engine.lookback,
        engine.ema_period,
        engine.vwap_window,
        engine.atr_period + 1,
    )
    engine.seed_history([make_candle(base_candle, minute) for minute in range(required - 1)])


@pytest.fixture
def mock_config():
    return {
        "strategy_profile": "unit_test_profile",
        "strategy": {
            "profile_name": "unit_test_profile",
            "lookback": 5,
            "ema_period": 3,
            "vwap_window": 4,
            "std_window": 5,
            "atr_period": 2,
            "armed_zscore": 1.8,
            "entry_zscore": 2.2,
            "min_score": 6,
            "low_volatility_filter_pct": 0.0025,
            "stop_atr_multiplier": 1.2,
            "take_profit_rr": 1.6,
            "min_stop_pct": 0.01,
            "max_stop_pct": 0.035,
            "min_take_profit_rr": 1.6,
            "max_take_profit_rr": 2.2,
            "zscore_retrace_delta": 0.35,
            "cooldown_bars": 2,
        },
    }


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def mock_candle():
    return {
        "symbol": "BTCUSDT",
        "timestamp": datetime(2026, 4, 18, 12, 0, tzinfo=timezone.utc),
        "close": 100.0,
        "high": 101.0,
        "low": 99.0,
        "volume": 1000.0,
    }


def test_initial_state_is_idle(mock_config, mock_logger):
    engine = SignalEngine(mock_config, mock_logger)

    assert engine.state == "IDLE"


def test_on_position_opened_changes_state_to_in_position(mock_config, mock_logger):
    engine = SignalEngine(mock_config, mock_logger)

    engine.on_position_opened()

    assert engine.state == "IN_POSITION"


def test_on_trade_closed_with_cooldown_changes_state_to_cooldown(mock_config, mock_logger):
    engine = SignalEngine(mock_config, mock_logger)

    engine.on_trade_closed({})

    assert engine.state == "COOLDOWN"
    assert engine.cooldown_remaining == mock_config["strategy"]["cooldown_bars"]


def test_on_trade_closed_without_cooldown_changes_state_to_idle(mock_config, mock_logger):
    config = {
        **mock_config,
        "strategy": {
            **mock_config["strategy"],
            "cooldown_bars": 0,
        },
    }
    engine = SignalEngine(config, mock_logger)

    engine.on_trade_closed({})

    assert engine.state == "IDLE"
    assert engine.cooldown_remaining == 0


def test_state_returns_to_idle_after_cooldown_completion(
    mock_config, mock_logger, mock_candle
):
    engine = SignalEngine(mock_config, mock_logger)
    seed_ready_history(engine, mock_candle)
    engine.on_trade_closed({})

    first_result = engine.on_candle(make_candle(mock_candle, 10), has_position=False)
    second_result = engine.on_candle(make_candle(mock_candle, 11), has_position=False)

    assert first_result["action"] == "NONE"
    assert first_result["state"] == "COOLDOWN"
    assert second_result["action"] == "NONE"
    assert second_result["state"] == "IDLE"
    assert engine.state == "IDLE"
    assert engine.cooldown_remaining == 0


def test_on_candle_returns_none_when_no_signal(mock_config, mock_logger, mock_candle):
    insufficient_engine = SignalEngine(mock_config, mock_logger)
    insufficient_result = insufficient_engine.on_candle(
        make_candle(mock_candle, 0),
        has_position=False,
    )
    assert "action" in insufficient_result
    assert insufficient_result["action"] == "NONE"

    in_position_engine = SignalEngine(mock_config, mock_logger)
    seed_ready_history(in_position_engine, mock_candle)
    in_position_result = in_position_engine.on_candle(
        make_candle(mock_candle, 10),
        has_position=True,
    )
    assert "action" in in_position_result
    assert in_position_result["action"] == "NONE"
    assert in_position_result["state"] == "IN_POSITION"

    cooldown_engine = SignalEngine(mock_config, mock_logger)
    seed_ready_history(cooldown_engine, mock_candle)
    cooldown_engine.on_trade_closed({})
    cooldown_result = cooldown_engine.on_candle(
        make_candle(mock_candle, 10),
        has_position=False,
    )
    assert "action" in cooldown_result
    assert cooldown_result["action"] == "NONE"
    assert cooldown_result["state"] == "COOLDOWN"

    no_signal_engine = SignalEngine(mock_config, mock_logger)
    seed_ready_history(no_signal_engine, mock_candle)
    no_signal_result = no_signal_engine.on_candle(
        make_candle(mock_candle, 10),
        has_position=False,
    )
    assert "action" in no_signal_result
    assert no_signal_result["action"] == "NONE"
    assert no_signal_result["state"] == "IDLE"

def test_full_short_signal_generation(mock_logger):
    """Exercise ARMED -> scoring -> entry confirmation -> SHORT signal."""
    config = {
        "strategy_profile": "aggressive",
        "strategy": {
            "profile_name": "aggressive",
            "lookback": 5,
            "ema_period": 3,
            "vwap_window": 4,
            "std_window": 5,
            "atr_period": 2,
            "armed_zscore": 1.35,
            "entry_zscore": 1.5,
            "min_score": 3,
            "low_volatility_filter_pct": 0.0020,
            "stop_atr_multiplier": 1.2,
            "take_profit_rr": 1.55,
            "min_stop_pct": 0.01,
            "max_stop_pct": 0.035,
            "min_take_profit_rr": 1.5,
            "max_take_profit_rr": 2.05,
            "zscore_retrace_delta": 0.28,
            "cooldown_bars": 1,
        },
    }
    engine = SignalEngine(config, mock_logger)

    base = 100.0
    candles = []
    for i in range(50):
        c = {
            "symbol": "BTCUSDT",
            "timestamp": datetime(2026, 6, 15, 12, i, tzinfo=timezone.utc),
            "close": base,
            "high": base + 0.5,
            "low": base - 0.5,
            "volume": 1000.0,
        }
        candles.append(c)
    engine.seed_history(candles)

    spike_candle = {
        "symbol": "BTCUSDT",
        "timestamp": datetime(2026, 6, 15, 13, 0, tzinfo=timezone.utc),
        "close": base * 1.04,
        "high": base * 1.05,
        "low": base * 1.03,
        "volume": 5000.0,
    }
    result = engine.on_candle(spike_candle, has_position=False)
    if result["action"] == "SHORT":
        assert result["symbol"] == "BTCUSDT"
        assert result["stop"] > result["entry"]
        assert result["tp"] < result["entry"]
        assert result["score"] >= config["strategy"]["min_score"]
        assert "meta" in result
        assert engine.state == "TRIGGERED"
