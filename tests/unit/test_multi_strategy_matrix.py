"""Tests for multi-strategy matrix builder — T4561-T4590."""
from __future__ import annotations

import json

import pytest

from core.multi_strategy_matrix import (
    ExperimentMatrix,
    MatrixRow,
    build_experiment_matrix,
    matrix_to_dict,
    matrix_to_json,
)
from core.strategy_research_parameters import ParameterSet


def _make_param_sets():
    return [
        ParameterSet(parameter_set_id="breakout_ps_001", strategy_id="breakout", preset_name="balanced", parameters={"lookback": 20}),
        ParameterSet(parameter_set_id="momentum_ps_001", strategy_id="momentum", preset_name="balanced", parameters={"lookback": 30}),
    ]


class TestMatrixBuilder:
    def test_builds_matrix(self):
        matrix = build_experiment_matrix(
            strategy_ids=["breakout", "momentum"],
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframes=["5m", "15m"],
            split_ids=["split_0", "split_1"],
            parameter_sets=_make_param_sets(),
        )
        assert matrix.total_rows > 0
        assert matrix.strategy_count == 2
        assert matrix.symbol_count == 2
        assert matrix.timeframe_count == 2

    def test_row_count(self):
        matrix = build_experiment_matrix(
            strategy_ids=["breakout"],
            symbols=["BTCUSDT"],
            timeframes=["5m"],
            split_ids=["split_0"],
            parameter_sets=[ParameterSet(parameter_set_id="ps_1", strategy_id="breakout", preset_name="b", parameters={"x": 1})],
        )
        assert matrix.total_rows == 1

    def test_deterministic_row_ids(self):
        m1 = build_experiment_matrix(
            strategy_ids=["breakout"], symbols=["BTCUSDT"], timeframes=["5m"],
            split_ids=["s0"], parameter_sets=_make_param_sets(),
        )
        m2 = build_experiment_matrix(
            strategy_ids=["breakout"], symbols=["BTCUSDT"], timeframes=["5m"],
            split_ids=["s0"], parameter_sets=_make_param_sets(),
        )
        for a, b in zip(m1.rows, m2.rows):
            assert a.matrix_row_id == b.matrix_row_id

    def test_sorted_order(self):
        matrix = build_experiment_matrix(
            strategy_ids=["momentum", "breakout"],
            symbols=["ETHUSDT", "BTCUSDT"],
            timeframes=["15m", "5m"],
            split_ids=["s1", "s0"],
            parameter_sets=_make_param_sets(),
        )
        # Rows should be sorted by strategy, symbol, timeframe, split
        for i in range(1, len(matrix.rows)):
            prev = matrix.rows[i - 1]
            curr = matrix.rows[i]
            assert (prev.strategy_id, prev.symbol, prev.timeframe, prev.split_id) <= \
                   (curr.strategy_id, curr.symbol, curr.timeframe, curr.split_id)

    def test_release_hold(self):
        matrix = build_experiment_matrix(
            strategy_ids=["breakout"], symbols=["BTCUSDT"], timeframes=["5m"],
            split_ids=["s0"], parameter_sets=_make_param_sets(),
        )
        for row in matrix.rows:
            assert row.release_hold == "HOLD"

    def test_fixture_path_format(self):
        matrix = build_experiment_matrix(
            strategy_ids=["breakout"], symbols=["BTCUSDT"], timeframes=["5m"],
            split_ids=["s0"], parameter_sets=_make_param_sets(),
        )
        assert matrix.rows[0].fixture_path.endswith(".csv")

    def test_missing_fixture_handling(self):
        """Matrix should build even if fixture doesn't exist (validation later)."""
        matrix = build_experiment_matrix(
            strategy_ids=["breakout"], symbols=["NONEXISTENT"], timeframes=["1h"],
            split_ids=["s0"], parameter_sets=_make_param_sets(),
            fixture_dir="/nonexistent",
        )
        assert matrix.total_rows == 1


class TestMatrixSerialization:
    def test_to_dict(self):
        matrix = build_experiment_matrix(
            strategy_ids=["breakout"], symbols=["BTCUSDT"], timeframes=["5m"],
            split_ids=["s0"], parameter_sets=_make_param_sets(),
        )
        d = matrix_to_dict(matrix)
        assert d["matrix_id"] == "multi_strategy_experiment_matrix"
        assert d["total_rows"] == matrix.total_rows

    def test_deterministic_json(self):
        matrix = build_experiment_matrix(
            strategy_ids=["breakout"], symbols=["BTCUSDT"], timeframes=["5m"],
            split_ids=["s0"], parameter_sets=_make_param_sets(),
        )
        j1 = matrix_to_json(matrix)
        j2 = matrix_to_json(matrix)
        assert j1 == j2
