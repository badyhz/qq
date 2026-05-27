"""Tests for read-only hook invariants — pure pytest, no I/O."""
import pytest

from core.read_only_hook_contract import build_read_only_hook_input
from core.read_only_hook_invariants import (
    INVARIANT_IDS,
    InvariantCheckResult,
    InvariantResult,
    check_invariants,
    invariant_check_result_to_dict,
    invariant_result_to_dict,
)


class TestInvariants:
    def test_clean_input_passes(self):
        inp = build_read_only_hook_input(
            hook_id="h1",
            operation_kind="query",
            payload={"symbol": "BTCUSDT"},
            permission_flags=["read"],
            context={"scope": "test"},
        )
        result = check_invariants(inp)
        assert isinstance(result, InvariantCheckResult)
        assert result.all_passed is True
        assert result.failed_count == 0

    def test_all_invariant_ids_present(self):
        assert len(INVARIANT_IDS) == 5
        assert "no_mutation" in INVARIANT_IDS
        assert "no_network" in INVARIANT_IDS
        assert "no_secrets" in INVARIANT_IDS
        assert "no_live_paths" in INVARIANT_IDS
        assert "no_planner" in INVARIANT_IDS

    def test_deterministic(self):
        inp = build_read_only_hook_input(
            "h1", "query", {"k": "v"}, ["read"], {"c": 1}
        )
        r1 = invariant_check_result_to_dict(check_invariants(inp))
        r2 = invariant_check_result_to_dict(check_invariants(inp))
        assert r1 == r2
