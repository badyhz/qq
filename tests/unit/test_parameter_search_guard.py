"""Tests for parameter search guard — T4501-T4530."""
from __future__ import annotations

import pytest

from core.parameter_search_guard import SearchBudgetGuardResult, check_search_budget


class TestSearchBudgetGuard:
    def test_within_budget(self):
        result = check_search_budget(50, search_budget=100)
        assert result.allowed is True
        assert result.budget_truncated is False
        assert result.overfit_warning is False

    def test_strict_mode_fail(self):
        result = check_search_budget(200, search_budget=100, mode="strict")
        assert result.allowed is False
        assert any("STRICT" in w for w in result.warnings)

    def test_truncate_mode(self):
        result = check_search_budget(200, search_budget=100, mode="truncate")
        assert result.allowed is True
        assert result.budget_truncated is True
        assert result.overfit_warning is True
        assert any("BUDGET_TRUNCATED" in w for w in result.warnings)

    def test_small_fixture_warning(self):
        result = check_search_budget(50, search_budget=100, fixture_row_count=10, min_fixture_rows=100)
        assert result.small_fixture_warning is True
        assert any("SMALL_FIXTURE" in w for w in result.warnings)

    def test_no_small_fixture_warning_when_sufficient(self):
        result = check_search_budget(50, search_budget=100, fixture_row_count=500, min_fixture_rows=100)
        assert result.small_fixture_warning is False

    def test_exact_budget(self):
        result = check_search_budget(100, search_budget=100)
        assert result.allowed is True
        assert result.budget_truncated is False

    def test_budget_bypass_impossible_in_strict(self):
        # Even with truncate mode, strict should always fail over budget
        result = check_search_budget(999999, search_budget=10, mode="strict")
        assert result.allowed is False
