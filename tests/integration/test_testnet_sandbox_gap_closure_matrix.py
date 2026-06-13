"""Test testnet sandbox gap closure matrix."""
import pytest
from src.runtime_integrations.testnet_sandbox.gap_closure_matrix import get_gaps, render_closure_matrix, render_next_stage_blockers


def test_gaps_exist():
    gaps = get_gaps()
    assert len(gaps) > 0


def test_gaps_have_required_categories():
    gaps = get_gaps()
    categories = {g.category for g in gaps}
    required = {"adapter interface", "credential vault", "human approval", "risk controls", "kill switch"}
    assert required.issubset(categories)


def test_gaps_include_blocking():
    gaps = get_gaps()
    blocking = [g for g in gaps if g.blocking]
    assert len(blocking) > 0


def test_closure_matrix_contains_not_ready():
    report = render_closure_matrix()
    assert "TESTNET_SANDBOX_NOT_READY_FOR_SUBMIT" in report


def test_next_stage_blockers_non_empty():
    report = render_next_stage_blockers()
    assert len(report) > 100
    assert "T110001" in report
