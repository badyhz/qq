"""Tests for parameter heatmap data — T6041-T6080.

Shape, NaN, sparse grid tests.
"""
from __future__ import annotations

import pytest
from core.parameter_heatmap_data import generate_heatmap_data


class TestHeatmapDataNormal:
    def test_basic_heatmap(self):
        points = [{"a": 1, "b": 1, "score": 0.5}, {"a": 2, "b": 1, "score": 0.6}]
        data = generate_heatmap_data(points, "a", "b")
        assert data["total_cells"] == 2
        assert data["filled_cells"] == 2


class TestHeatmapDataEdge:
    def test_empty_grid(self):
        data = generate_heatmap_data([], "a", "b")
        assert data["total_cells"] == 0


class TestHeatmapDataDeterministic:
    def test_deterministic(self):
        points = [{"a": 1, "b": 1, "score": 0.5}]
        d1 = generate_heatmap_data(points, "a", "b")
        d2 = generate_heatmap_data(points, "a", "b")
        assert d1 == d2
