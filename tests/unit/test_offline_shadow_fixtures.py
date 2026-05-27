import json
import os

import pytest

from core.offline_shadow_fixture_loader import (
    load_bars,
    load_outcomes,
    load_signals,
    load_symbols,
    load_timeframes,
)

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "offline_shadow_research"
)

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
TIMEFRAMES = ["5m", "15m"]

EXPECTED_BAR_KEYS = {"timestamp_index", "open", "high", "low", "close", "volume"}
EXPECTED_SIGNAL_KEYS = {"timestamp_index", "direction", "strength", "entry_price"}
EXPECTED_OUTCOME_KEYS = {
    "timestamp_index",
    "exit_price",
    "return_r",
    "hold_bars",
    "mfe_r",
    "mae_r",
}


# --- fixture file existence and validity ---


class TestFixtureFiles:
    @pytest.mark.parametrize("name", [
        "symbols.json",
        "timeframes.json",
        "bars_BTCUSDT_5m.json",
        "bars_BTCUSDT_15m.json",
        "bars_ETHUSDT_5m.json",
        "bars_ETHUSDT_15m.json",
        "signals_BTCUSDT_5m.json",
        "signals_BTCUSDT_15m.json",
        "signals_ETHUSDT_5m.json",
        "signals_ETHUSDT_15m.json",
        "outcomes_BTCUSDT_5m.json",
        "outcomes_BTCUSDT_15m.json",
        "outcomes_ETHUSDT_5m.json",
        "outcomes_ETHUSDT_15m.json",
    ])
    def test_file_exists(self, name):
        path = os.path.join(FIXTURE_DIR, name)
        assert os.path.exists(path), f"Missing {name}"

    @pytest.mark.parametrize("name", [
        "symbols.json",
        "timeframes.json",
        "bars_BTCUSDT_5m.json",
        "bars_BTCUSDT_15m.json",
        "bars_ETHUSDT_5m.json",
        "bars_ETHUSDT_15m.json",
        "signals_BTCUSDT_5m.json",
        "signals_BTCUSDT_15m.json",
        "signals_ETHUSDT_5m.json",
        "signals_ETHUSDT_15m.json",
        "outcomes_BTCUSDT_5m.json",
        "outcomes_BTCUSDT_15m.json",
        "outcomes_ETHUSDT_5m.json",
        "outcomes_ETHUSDT_15m.json",
    ])
    def test_valid_json(self, name):
        path = os.path.join(FIXTURE_DIR, name)
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, (list, dict))


# --- loader tests ---


class TestLoadSymbols:
    def test_returns_list(self):
        result = load_symbols(FIXTURE_DIR)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_expected_keys(self):
        for item in load_symbols(FIXTURE_DIR):
            assert set(item.keys()) == {"symbol", "base_asset", "quote_asset", "exchange"}

    def test_symbols_match(self):
        syms = [s["symbol"] for s in load_symbols(FIXTURE_DIR)]
        assert syms == SYMBOLS


class TestLoadTimeframes:
    def test_returns_list(self):
        result = load_timeframes(FIXTURE_DIR)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_expected_keys(self):
        for item in load_timeframes(FIXTURE_DIR):
            assert set(item.keys()) == {"label", "minutes"}


class TestLoadBars:
    @pytest.mark.parametrize("symbol", SYMBOLS)
    @pytest.mark.parametrize("timeframe", TIMEFRAMES)
    def test_count_and_keys(self, symbol, timeframe):
        bars = load_bars(FIXTURE_DIR, symbol, timeframe)
        assert len(bars) == 20
        for bar in bars:
            assert set(bar.keys()) == EXPECTED_BAR_KEYS


class TestLoadSignals:
    @pytest.mark.parametrize("symbol", SYMBOLS)
    @pytest.mark.parametrize("timeframe", TIMEFRAMES)
    def test_count_and_keys(self, symbol, timeframe):
        signals = load_signals(FIXTURE_DIR, symbol, timeframe)
        assert len(signals) == 8
        for sig in signals:
            assert set(sig.keys()) == EXPECTED_SIGNAL_KEYS


class TestLoadOutcomes:
    @pytest.mark.parametrize("symbol", SYMBOLS)
    @pytest.mark.parametrize("timeframe", TIMEFRAMES)
    def test_count_and_keys(self, symbol, timeframe):
        outcomes = load_outcomes(FIXTURE_DIR, symbol, timeframe)
        assert len(outcomes) == 8
        for out in outcomes:
            assert set(out.keys()) == EXPECTED_OUTCOME_KEYS
