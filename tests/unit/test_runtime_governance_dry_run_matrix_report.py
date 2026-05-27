"""Tests for runtime_governance_dry_run_matrix_report.

Deterministic. No I/O. No network. No random. No timestamps.
"""

from __future__ import annotations

import pytest

from core.runtime_governance_dry_run_matrix_report import (
    RuntimeGovernanceDryRunMatrixRow,
    build_runtime_governance_dry_run_matrix_report,
    dry_run_matrix_to_dict,
    dry_run_matrix_to_markdown,
)


# ── fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def matrix() -> list[RuntimeGovernanceDryRunMatrixRow]:
    return build_runtime_governance_dry_run_matrix_report()


# ── tests ──────────────────────────────────────────────────────────────


def test_matrix_includes_all_five_kinds(matrix):
    kinds = [row.kind for row in matrix]
    assert kinds == ["pass", "fail", "blocked", "warn_like", "invalid_contract"]


def test_pass_kind_ready_for_runtime(matrix):
    row = next(r for r in matrix if r.kind == "pass")
    assert row.ready_for_runtime is True
    assert row.final_verdict == "PASS"


def test_blocked_kind_not_ready(matrix):
    row = next(r for r in matrix if r.kind == "blocked")
    assert row.ready_for_runtime is False
    assert row.blocker_count > 0


def test_dict_deterministic(matrix):
    d1 = dry_run_matrix_to_dict(matrix)
    d2 = dry_run_matrix_to_dict(matrix)
    assert d1 == d2


def test_markdown_deterministic(matrix):
    md1 = dry_run_matrix_to_markdown(matrix)
    md2 = dry_run_matrix_to_markdown(matrix)
    assert md1 == md2
    assert "# Runtime Governance Dry-Run Matrix Report" in md1
    assert "| pass |" in md1
    assert "| blocked |" in md1
