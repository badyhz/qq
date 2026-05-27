"""Offline shadow fixture loader -- loads fixture data from JSON files.

Each function loads a specific fixture type from the fixture directory.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_symbols(fixture_dir: str) -> list[dict]:
    """Load symbol definitions from symbols.json."""
    path = Path(fixture_dir) / "symbols.json"
    with open(path) as f:
        return json.load(f)


def load_timeframes(fixture_dir: str) -> list[dict]:
    """Load timeframe definitions from timeframes.json."""
    path = Path(fixture_dir) / "timeframes.json"
    with open(path) as f:
        return json.load(f)


def load_bars(fixture_dir: str, symbol: str, timeframe: str) -> list[dict]:
    """Load bar data for a symbol/timeframe pair."""
    path = Path(fixture_dir) / f"bars_{symbol}_{timeframe}.json"
    with open(path) as f:
        return json.load(f)


def load_signals(fixture_dir: str, symbol: str, timeframe: str) -> list[dict]:
    """Load signal data for a symbol/timeframe pair."""
    path = Path(fixture_dir) / f"signals_{symbol}_{timeframe}.json"
    with open(path) as f:
        return json.load(f)


def load_outcomes(fixture_dir: str, symbol: str, timeframe: str) -> list[dict]:
    """Load outcome data for a symbol/timeframe pair."""
    path = Path(fixture_dir) / f"outcomes_{symbol}_{timeframe}.json"
    with open(path) as f:
        return json.load(f)


def load_fixtures(fixture_dir: str) -> list[dict]:
    """Load experiment fixture files from a directory.

    Loads experiment_*.json files (not bars/outcomes/signals).

    Raises
    ------
    FileNotFoundError
        If fixture_dir does not exist.
    ValueError
        If no experiment fixtures found.
    """
    path = Path(fixture_dir)
    if not path.exists():
        raise FileNotFoundError(f"Fixture directory not found: {fixture_dir}")

    fixtures: list[dict] = []
    for f in sorted(path.glob("experiment_*.json")):
        with open(f) as fh:
            data = json.load(fh)
            if isinstance(data, list):
                fixtures.extend(data)
            else:
                fixtures.append(data)

    if not fixtures:
        raise ValueError(f"No experiment fixtures found in {fixture_dir}")

    return fixtures


def validate_fixture(fixture: dict) -> bool:
    """Check that a fixture dict has all required experiment keys.

    Required keys: experiment_id, symbol, timeframe, window, parameter_set.
    """
    required = {"experiment_id", "symbol", "timeframe", "window", "parameter_set"}
    return required.issubset(fixture.keys())
