import json
import os


def load_symbols(fixture_dir: str) -> list[dict]:
    path = os.path.join(fixture_dir, "symbols.json")
    with open(path) as f:
        return json.load(f)


def load_timeframes(fixture_dir: str) -> list[dict]:
    path = os.path.join(fixture_dir, "timeframes.json")
    with open(path) as f:
        return json.load(f)


def load_bars(fixture_dir: str, symbol: str, timeframe: str) -> list[dict]:
    path = os.path.join(fixture_dir, f"bars_{symbol}_{timeframe}.json")
    with open(path) as f:
        return json.load(f)


def load_signals(fixture_dir: str, symbol: str, timeframe: str) -> list[dict]:
    path = os.path.join(fixture_dir, f"signals_{symbol}_{timeframe}.json")
    with open(path) as f:
        return json.load(f)


def load_outcomes(fixture_dir: str, symbol: str, timeframe: str) -> list[dict]:
    path = os.path.join(fixture_dir, f"outcomes_{symbol}_{timeframe}.json")
    with open(path) as f:
        return json.load(f)
