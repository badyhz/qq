"""Tests for performance guard — T5011-T5040."""
from __future__ import annotations

import pytest

from core.research_workbench_performance_guard import PerformanceGuardResult, check_performance_guard


class TestPerformanceGuard:
    def test_within_limits(self):
        result = check_performance_guard(100, chunk_size=25, max_rows=10000)
        assert result.allowed is True
        assert result.warnings == []

    def test_max_rows_exceeded(self):
        result = check_performance_guard(20000, chunk_size=25, max_rows=10000)
        assert result.allowed is False
        assert any("MAX_ROWS" in w for w in result.warnings)

    def test_invalid_chunk_size(self):
        result = check_performance_guard(100, chunk_size=0)
        assert any("CHUNK" in w for w in result.warnings)

    def test_exact_max_rows(self):
        result = check_performance_guard(10000, max_rows=10000)
        assert result.allowed is True
