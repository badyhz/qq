"""Parameter search guard — explicit budget enforcement and warnings.

Provides strict/truncation modes, overfit warnings, and small fixture warnings.

No network, no exchange, no live, no submit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class SearchBudgetGuardResult:
    """Result of a search budget guard check."""
    allowed: bool
    budget: int
    requested_combinations: int
    mode: str  # "strict", "truncate"
    budget_truncated: bool
    overfit_warning: bool
    small_fixture_warning: bool
    warnings: List[str]


def check_search_budget(
    requested_combinations: int,
    search_budget: int,
    mode: str = "truncate",
    fixture_row_count: int = 0,
    min_fixture_rows: int = 100,
) -> SearchBudgetGuardResult:
    """Check if requested combinations fit within search budget.

    mode="strict": fail if over budget
    mode="truncate": allow but mark truncated
    """
    warnings: List[str] = []
    budget_truncated = False
    overfit_warning = False
    small_fixture_warning = False
    allowed = True

    if requested_combinations > search_budget:
        if mode == "strict":
            allowed = False
            warnings.append(f"STRICT: {requested_combinations} combinations exceed budget {search_budget}")
        else:
            budget_truncated = True
            overfit_warning = True
            warnings.append(
                f"BUDGET_TRUNCATED: {requested_combinations} > {search_budget}, "
                f"truncated to {search_budget}"
            )

    if fixture_row_count > 0 and fixture_row_count < min_fixture_rows:
        small_fixture_warning = True
        warnings.append(
            f"SMALL_FIXTURE: {fixture_row_count} rows < {min_fixture_rows} minimum"
        )

    return SearchBudgetGuardResult(
        allowed=allowed,
        budget=search_budget,
        requested_combinations=requested_combinations,
        mode=mode,
        budget_truncated=budget_truncated,
        overfit_warning=overfit_warning,
        small_fixture_warning=small_fixture_warning,
        warnings=warnings,
    )
