"""Tests for parameter robustness grid — T5921-T5960.

Normal, boundary, invalid budget tests.
"""
from __future__ import annotations

import pytest
from core.parameter_robustness_grid import build_perturbation_grid, grid_to_dict


class TestPerturbationGridNormal:
    def test_basic_grid(self):
        points = build_perturbation_grid(
            {"a": 1, "b": 2},
            {"a": [1, 2, 3], "b": [2, 3, 4]},
        )
        assert len(points) > 0

    def test_grid_respects_budget(self):
        points = build_perturbation_grid(
            {"a": 1}, {"a": list(range(100))}, search_budget=10
        )
        assert len(points) <= 10


class TestPerturbationGridEdge:
    def test_empty_ranges(self):
        points = build_perturbation_grid({"a": 1}, {})
        assert len(points) == 1  # just the base


class TestPerturbationGridAdversarial:
    def test_budget_one(self):
        points = build_perturbation_grid(
            {"a": 1}, {"a": [1, 2, 3]}, search_budget=1
        )
        assert len(points) <= 1


class TestPerturbationGridDeterministic:
    def test_deterministic(self):
        args = ({"a": 1}, {"a": [1, 2, 3]})
        p1 = grid_to_dict(build_perturbation_grid(*args))
        p2 = grid_to_dict(build_perturbation_grid(*args))
        assert p1 == p2
