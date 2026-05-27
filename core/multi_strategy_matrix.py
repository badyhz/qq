"""Multi-strategy matrix builder — combines strategies, symbols, timeframes, splits, parameter sets.

Deterministic row ordering, stable ids, no network, no exchange.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.strategy_research_parameters import ParameterSet


@dataclass(frozen=True)
class MatrixRow:
    """A single matrix row representing one experiment."""
    matrix_row_id: str
    strategy_id: str
    strategy_family: str
    symbol: str
    timeframe: str
    split_id: str
    parameter_set_id: str
    fixture_path: str
    dataset_id: str
    run_mode: str = "offline_research"
    release_hold: str = "HOLD"


@dataclass(frozen=True)
class ExperimentMatrix:
    """A complete experiment matrix."""
    matrix_id: str
    rows: Tuple[MatrixRow, ...]
    strategy_count: int
    symbol_count: int
    timeframe_count: int
    total_rows: int


# Strategy family mapping
_STRATEGY_FAMILIES = {
    "breakout": "breakout",
    "mean_reversion": "mean_reversion",
    "momentum": "momentum",
    "volatility_compression": "volatility_compression",
}


def _make_row_id(strategy_id: str, symbol: str, timeframe: str, split_id: str, ps_id: str) -> str:
    """Generate deterministic matrix row id."""
    raw = f"{strategy_id}:{symbol}:{timeframe}:{split_id}:{ps_id}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return f"row_{digest}"


def build_experiment_matrix(
    strategy_ids: List[str],
    symbols: List[str],
    timeframes: List[str],
    split_ids: List[str],
    parameter_sets: List[ParameterSet],
    fixture_dir: str = "tests/fixtures/historical_backtest_lab",
) -> ExperimentMatrix:
    """Build experiment matrix from strategies, symbols, timeframes, splits, parameter sets.

    Deterministic row ordering. No network. No exchange.
    """
    # Sort all inputs for determinism
    strategy_ids = sorted(strategy_ids)
    symbols = sorted(symbols)
    timeframes = sorted(timeframes)
    split_ids = sorted(split_ids)

    rows: List[MatrixRow] = []
    for sid in strategy_ids:
        family = _STRATEGY_FAMILIES.get(sid, sid)
        # Get parameter sets for this strategy
        strategy_ps = [ps for ps in parameter_sets if ps.strategy_id == sid]
        if not strategy_ps:
            continue
        for symbol in symbols:
            for tf in timeframes:
                for split_id in split_ids:
                    for ps in sorted(strategy_ps, key=lambda p: p.parameter_set_id):
                        dataset_id = f"{symbol}_{tf}_fixture"
                        fixture_path = f"{fixture_dir}/{symbol.lower()}_{tf}_clean.csv"
                        row_id = _make_row_id(sid, symbol, tf, split_id, ps.parameter_set_id)
                        rows.append(MatrixRow(
                            matrix_row_id=row_id,
                            strategy_id=sid,
                            strategy_family=family,
                            symbol=symbol,
                            timeframe=tf,
                            split_id=split_id,
                            parameter_set_id=ps.parameter_set_id,
                            fixture_path=fixture_path,
                            dataset_id=dataset_id,
                        ))

    return ExperimentMatrix(
        matrix_id="multi_strategy_experiment_matrix",
        rows=tuple(rows),
        strategy_count=len(strategy_ids),
        symbol_count=len(symbols),
        timeframe_count=len(timeframes),
        total_rows=len(rows),
    )


def matrix_to_dict(matrix: ExperimentMatrix) -> Dict[str, Any]:
    """Serialize matrix to dict."""
    return {
        "matrix_id": matrix.matrix_id,
        "strategy_count": matrix.strategy_count,
        "symbol_count": matrix.symbol_count,
        "timeframe_count": matrix.timeframe_count,
        "total_rows": matrix.total_rows,
        "rows": [
            {
                "matrix_row_id": r.matrix_row_id,
                "strategy_id": r.strategy_id,
                "strategy_family": r.strategy_family,
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "split_id": r.split_id,
                "parameter_set_id": r.parameter_set_id,
                "fixture_path": r.fixture_path,
                "dataset_id": r.dataset_id,
                "run_mode": r.run_mode,
                "release_hold": r.release_hold,
            }
            for r in matrix.rows
        ],
    }


def matrix_to_json(matrix: ExperimentMatrix, indent: int = 2) -> str:
    """Serialize matrix to JSON."""
    return json.dumps(matrix_to_dict(matrix), sort_keys=True, indent=indent)
