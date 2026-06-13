"""Test sandbox final blocker matrix."""
import pytest
from src.runtime_integrations.testnet_final_gate.final_blocker_matrix import get_blockers, render_matrix, render_next_stage_blockers

def test_blockers_exist():
    b = get_blockers()
    assert len(b) >= 10

def test_has_blocking_items():
    b = get_blockers()
    blocking = [x for x in b if x.status == "BLOCKING"]
    assert len(blocking) >= 5

def test_matrix_contains_not_allowed():
    m = render_matrix()
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in m

def test_next_stage_non_empty():
    r = render_next_stage_blockers()
    assert "T140001" in r
